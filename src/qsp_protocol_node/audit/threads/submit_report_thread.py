####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread submitting the report for the QSP Audit node implementation.
"""

import jsonschema
import json
import os
import traceback

from evt import is_audit
from evt import is_police_check
from utils.eth import DeduplicationException
from utils.eth import mk_read_only_call
from utils.eth import send_signed_transaction
from utils.eth.tx import TransactionNotConfirmedException

from .qsp_thread import TimeIntervalPollingThread
from ..vulnerabilities_set import VulnerabilitiesSet


class SubmitReportThread(TimeIntervalPollingThread):
    # Similarity threshold to deem a report correct
    __SIMILARITY_THRESHOLD = .6

    def process_events_to_be_submitted(self):
        self.config.event_pool_manager.process_events_to_be_submitted(
            self.__process_submission_request
        )

    def __check_report(self, evt, request_id):
        """
        Returns true if the report is correct and false otherwise.
        """
        police_report = json.loads(evt['full_report'])
        police_check_result = self.__is_report_deemed_correct(request_id, police_report)
        self.logger.debug("Police check: report {} correct".format(
            "is" if police_check_result else "is not"))
        return police_check_result

    def __process_submission_request(self, evt):
        try:
            tx_hash = None
            request_id = int(evt['request_id'])
            # If the audit is not a police check, submit it as a conventional audit
            if is_audit(evt):
                tx_hash = self.__submit_audit_report(
                    request_id,
                    evt['audit_state'],
                    evt['compressed_report'],
                )
            # If the audit is a police check, submit it as such
            elif is_police_check(evt):
                police_check_result = self.__check_report(evt, request_id)
                tx_hash = self.__submit_police_report(
                    request_id,
                    evt['compressed_report'],
                    is_verified=police_check_result
                )
            else:
                # Should never occur!
                raise Exception("Unknown report type")

            evt['tx_hash'] = tx_hash.hex()
            evt['status_info'] = 'Report submitted (waiting for confirmation)'
            self.config.event_pool_manager.set_evt_status_to_submitted(evt)
        except DeduplicationException as error:
            self.logger.debug(
                "Error when submitting report {0}".format(str(error))
            )
        except TransactionNotConfirmedException as error:
            error_msg = "A transaction occurred, but was then uncled and never recovered. {0}"
            self.logger.debug(error_msg.format(str(error)))
        except KeyError as error:
            self.logger.exception(
                "KeyError when processing submission event: {0}".format(str(error))
            )
        except Exception as error:
            self.logger.exception(
                "Error when processing submission event {0}: {1}.".format(
                    str(evt['request_id']),
                    str(error),
                ),
                requestId=evt['request_id'],
            )
            evt['status_info'] = traceback.format_exc()
            self.config.event_pool_manager.set_evt_status_to_error(evt)

    def __submit_audit_report(self, request_id, audit_state, compressed_report):
        """
        Submits the audit report to the entire QSP network.
        """
        # Convert from a bitstring to a bytes array
        compressed_report_bytes = self.config.web3_client.toBytes(hexstr=compressed_report)

        tx_hash = send_signed_transaction(self.config,
                                          self.config.audit_contract.functions.submitReport(
                                              request_id,
                                              audit_state,
                                              compressed_report_bytes))
        self.logger.debug("Audit report submitted", requestId=request_id)
        return tx_hash

    def __submit_police_report(self, request_id, compressed_report, is_verified):
        """
        Submits the police report to the entire QSP network.
        """
        # Convert from a bitstring to a bytes array
        compressed_report_bytes = self.config.web3_client.toBytes(hexstr=compressed_report)

        tx_hash = send_signed_transaction(self.config,
                                          self.config.audit_contract.functions.submitPoliceReport(
                                              request_id,
                                              compressed_report_bytes,
                                              is_verified))
        self.logger.debug("Police report submitted", requestId=request_id)
        return tx_hash

    def __is_report_deemed_correct(self, request_id, full_police_report):
        """
        Checks whether an audit report should be deemed correct using a police (full) report as a
        baseline for comparison. Reports are deemed correct if they have at least
        __SIMILARITY_THRESHOLD (%) of the vulnerabilities reported by the police.
        """
        compressed_audit_report = self.__get_report_in_blockchain(request_id)

        # If the compressed audit report cannot be found, just raise an exception.
        if compressed_audit_report is None:
            raise Exception(
                "Report for request_id {0} not found".format(request_id)
            )

        # Decompress the audit report
        try:
            decompressed_audit_report = self.config.report_encoder.decode_report(
                compressed_audit_report,
                request_id
            )
            self.__validate_json(decompressed_audit_report, request_id)
        except Exception as err:
            self.logger.debug("Cannot decompress the audit report: {0}".format(err))
            return False

        # Makes sure the contract_hashes in both the compressed report and the police match
        audit_contract_hash = decompressed_audit_report.get('contract_hash', "").lower()
        police_contract_hash = full_police_report.get('contract_hash', "").lower()
        if not audit_contract_hash or not police_contract_hash or audit_contract_hash != police_contract_hash:
            msg = "Police check: reports for request ID {0} have different contract hashes: {1} {2}"
            self.logger.debug(msg.format(str(request_id),
                                         str(decompressed_audit_report.get('contract_hash',
                                                                           None)),
                                         str(full_police_report.get('contract_hash', None))))
            return False

        # Makes sure that the audit statuses match
        audit_contract_status = decompressed_audit_report.get('status', "").lower()
        police_contract_status = full_police_report.get('status', "").lower()
        if not audit_contract_status or not police_contract_status or \
                audit_contract_status != police_contract_status:
            return False

        # If report exists, but building a vulnerability set fails,
        # deem the report as incorrect
        try:
            auditor_vulnerabilities = VulnerabilitiesSet.from_uncompressed_report(
                decompressed_audit_report
            )
        except Exception as err:
            self.logger.debug("Cannot build vulnerability set: {0}".format(err))
            return False

        police_vulnerabilities = VulnerabilitiesSet.from_uncompressed_report(full_police_report)

        # Accounts for the case where the police cannot find any
        # vulnerability
        if len(police_vulnerabilities) == 0:
            return True

        similarity = len(auditor_vulnerabilities & police_vulnerabilities) / len(
            police_vulnerabilities)
        return similarity >= SubmitReportThread.__SIMILARITY_THRESHOLD

    def __get_report_in_blockchain(self, request_id):
        """
        Gets a compressed report already stored in the blockchain.
        """
        compressed_report_bytes = mk_read_only_call(
            self.config,
            self.config.audit_contract.functions.getReport(request_id)
        )
        if compressed_report_bytes is None or len(compressed_report_bytes) == 0:
            return None

        return compressed_report_bytes.hex()

    def __validate_json(self, report, request_id):
        """
        Validate that the report conforms to the schema.
        """
        try:
            file_path = os.path.realpath(__file__)
            schema_file = '{0}/../../../../plugins/analyzers/schema/analyzer_integration.json'.format(
                os.path.dirname(file_path))
            with open(schema_file) as schema_data:
                schema = json.load(schema_data)
            jsonschema.validate(report, schema)
            return report
        except jsonschema.ValidationError as e:
            self.logger.exception(
                "Error: JSON could not be validated: {0}.".format(str(e)),
                zrequestId=request_id,
            )
            raise Exception("JSON could not be validated") from e

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        TimeIntervalPollingThread.__init__(
            self,
            config=config,
            target_function=self.process_events_to_be_submitted,
            thread_name="submission thread"
        )
