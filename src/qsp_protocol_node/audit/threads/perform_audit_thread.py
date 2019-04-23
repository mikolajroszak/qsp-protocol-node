####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread updating the min price for the QSP Audit node implementation.
"""
import traceback
import urllib
import os
import urllib.parse
import calendar
import time
import json
import copy
import threading

from threading import Thread
from evt import is_police_check
from utils.io import (
    fetch_file,
    digest,
    digest_file,
    read_file
)
from solc.exceptions import ContractsNotFound, SolcError
from solc import compile_standard
from subprocess import TimeoutExpired

from .qsp_thread import TimeIntervalPollingThread


class PerformAuditThread(TimeIntervalPollingThread):

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAuditData.sol#L14
    __AUDIT_STATE_SUCCESS = 4

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAuditData.sol#L15
    __AUDIT_STATE_ERROR = 5

    __AUDIT_STATUS_ERROR = "error"
    __AUDIT_STATUS_SUCCESS = "success"

    # Empty report for certain error cases
    __EMPTY_COMPRESSED_REPORT = ""

    def __process_incoming(self):
        self.config.event_pool_manager.process_incoming_events(
            self.__process_audit_request
        )

    def __create_err_result(self, errors, warnings, request_id, requestor, uri, target_contract):
        result = {
            'timestamp': calendar.timegm(time.gmtime()),
            'contract_uri': uri,
            'contract_hash': digest_file(target_contract),
            'requestor': requestor,
            'auditor': self.config.account,
            'request_id': request_id,
            'version': self.config.node_version,
            'audit_state': PerformAuditThread.__AUDIT_STATE_ERROR,
            'status': PerformAuditThread.__AUDIT_STATUS_ERROR,
        }
        if errors is not None and len(errors) != 0:
            result['compilation_errors'] = errors
        if warnings is not None and len(warnings) != 0:
            result['compilation_warnings'] = warnings

        return result

    def __compute_audit_result(self, wrappers, local_reports):
        # This is currently a very simple mechanism to claim an audit as
        # successful or not. A report is labelled as `success` IFF
        # at least one analyzer succeeds and no analyzers return error,
        # however some may timeout.
        audit_state = PerformAuditThread.__AUDIT_STATE_SUCCESS
        audit_status = PerformAuditThread.__AUDIT_STATUS_SUCCESS

        has_successful_analyzer = False

        for i, analyzer_report in enumerate(local_reports):

            # The next two fail safe checks should never kick in...

            # This is a fail safe mechanism (defensive programming)
            if 'analyzer' not in analyzer_report:
                analyzer_report['analyzer'] = {
                    'name': wrappers[i].analyzer_name
                }

            # Another fail safe mechanism (defensive programming)
            if 'status' not in analyzer_report:
                analyzer_report['status'] = 'error'
                errors = analyzer_report.get('errors', [])
                errors.append('Unknown error: cannot produce report')
                analyzer_report['errors'] = errors

            # Invariant: no analyzer report can ever be empty!

            if analyzer_report['status'] == 'error':
                audit_state = PerformAuditThread.__AUDIT_STATE_ERROR
                audit_status = PerformAuditThread.__AUDIT_STATUS_ERROR

            if analyzer_report['status'] == 'success':
                has_successful_analyzer = True

        if not has_successful_analyzer:
            audit_state = PerformAuditThread.__AUDIT_STATE_ERROR
            audit_status = PerformAuditThread.__AUDIT_STATUS_ERROR

        return audit_state, audit_status

    def check_compilation(self, contract, request_id, uri):
        self.logger.debug("Running compilation check. About to check {0}".format(contract),
                            requestId=request_id)
        parse_uri = urllib.parse.urlparse(uri)
        original_file_name = os.path.basename(parse_uri.path)
        temp_file_name = os.path.basename(contract)
        data = ""
        with open(contract, 'r') as myfile:
            data = myfile.read()
        warnings = []
        errors = []
        try:
            # Attempts to compile the target contract. If it fails, a ContractsNotFound
            # exception is thrown
            file_name = contract[contract.rfind('/') + 1:]
            output = compile_standard({'language': 'Solidity',
                                       'sources': {
                                           file_name: {'content': data}}}
                                      )
            for err in output.get('errors', []):
                if err["severity"] == "warning":
                    warnings += [err['formattedMessage'].replace(temp_file_name, original_file_name)]
                else:
                    errors += [err['formattedMessage'].replace(temp_file_name, original_file_name)]

        except ContractsNotFound as error:
            self.logger.debug(
                "ContractsNotFound before calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            errors += [str(error)]
        except SolcError as error:
            self.logger.debug(
                "SolcError before calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            errors += [str(error)]
        except KeyError as error:
            self.logger.error(
                "KeyError when calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            # This is thrown because a bug in our own code. We only log, but do not record the error
            # so that the analyzers are still executed.
        except Exception as error:
            self.logger.error(
                "Error before calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            errors += [str(error)]

        return warnings, errors

    def get_audit_report_from_analyzers(self, target_contract, requestor, uri, request_id):
        number_of_analyzers = len(self.config.analyzers)

        parse_uri = urllib.parse.urlparse(uri)
        original_file_name = os.path.basename(parse_uri.path)

        # Arrays to track different data from each analyzer,
        # each identified by a single position (analyzer_id)
        shared_reports = []
        local_reports = []
        report_locks = []
        wrappers = []
        timed_out_flags = []
        analyzer_threads = []
        start_times = []

        def check_contract(analyzer_id):
            report = {}
            has_timed_out = False

            try:
                report = self.config.analyzers[analyzer_id].check(
                    target_contract,
                    request_id,
                    original_file_name
                )
            except Exception as error:
                # Defer saving timeout errors for now as there is another
                # check later on (report timeouts only once)
                if isinstance(error, TimeoutExpired):
                    has_timed_out = True

                # Otherwise, save the error
                else:
                    errors = report.get('errors', [])
                    errors.append(str(error))

                report['status'] = 'error'

            # Make sure no race-condition between the wrappers and the current thread
            try:
                report_locks[analyzer_id].acquire()
                shared_reports[analyzer_id] = report
                timed_out_flags[analyzer_id] = has_timed_out
            finally:
                report_locks[analyzer_id].release()

        # Starts each analyzer thread
        for i, analyzer in enumerate(self.config.analyzers):
            shared_reports.append({})
            local_reports.append({})
            report_locks.append(threading.RLock())
            wrappers.append(self.config.analyzers[i].wrapper)
            timed_out_flags.append(False)

            thread_name = "{0}-analyzer-thread".format(wrappers[i].analyzer_name)
            analyzer_thread = Thread(target=check_contract, args=[i], name=thread_name)
            analyzer_threads.append(analyzer_thread)

            start_time = calendar.timegm(time.gmtime())
            start_times.append(start_time)

            analyzer_thread.start()

        for i in range(0, number_of_analyzers):
            analyzer_threads[i].join(wrappers[i].timeout_sec)

            # Make sure there is no race condition between the current thread
            # and the wrapper/analyzer thread when writing reports
            try:
                report_locks[i].acquire()
                local_reports[i] = copy.deepcopy(shared_reports[i])

                if analyzer_threads[i].is_alive():
                    timed_out_flags[i] = True
            finally:
                report_locks[i].release()

            local_reports[i]['analyzer'] = wrappers[i].get_metadata(
                target_contract,
                request_id,
                original_file_name
            )

            # NOTE
            # Due to timeout issues, one has to account for start/end
            # times at this point, rather than at the wrapper itself
            local_reports[i]['start_time'] = start_times[i]

            # If analyzer has timed out, report the error
            if timed_out_flags[i]:
                errors = local_reports[i].get('errors', [])
                errors.append(
                    "Time out occurred. Could not finish {0} within {1} seconds".format(
                        wrappers[i].analyzer_name,
                        wrappers[i].timeout_sec,
                    )
                )
                local_reports[i]['errors'] = errors
                local_reports[i]['status'] = 'timeout'

            # A timeout has not occurred. Register the end time
            end_time = calendar.timegm(time.gmtime())
            local_reports[i]['end_time'] = end_time

        audit_report = {
            'timestamp': calendar.timegm(time.gmtime()),
            'contract_uri': uri,
            'contract_hash': digest_file(target_contract),
            'requestor': requestor,
            'auditor': self.config.account,
            'request_id': request_id,
            'version': self.config.node_version,
        }

        audit_state, audit_status = self.__compute_audit_result(wrappers, local_reports)

        audit_report['audit_state'] = audit_state
        audit_report['status'] = audit_status

        if len(local_reports) > 0:
            audit_report['analyzers_reports'] = local_reports

        return audit_report

    def get_full_report(self, requestor, uri, request_id):
        """
        Produces the full report for a smart contract.
        """
        target_contract = fetch_file(uri)

        warnings, errors = self.check_compilation(target_contract, request_id, uri)
        audit_report = {}
        if len(errors) != 0:
            audit_report = self.__create_err_result(errors, warnings, request_id, requestor, uri,
                                                    target_contract)
        else:
            audit_report = self.get_audit_report_from_analyzers(target_contract, requestor, uri,
                                                                request_id)
            if len(warnings) != 0:
                audit_report['compilation_warnings'] = warnings

        self.logger.info(
            "Analyzer report contents",
            requestId=request_id,
            contents=audit_report,
        )
        return target_contract, audit_report

    def audit(self, requestor, uri, request_id, report_type):
        """
        Audits a target contract.
        """
        self.logger.info(
            "Executing {0} check on contract at {1}".format(report_type, uri),
            requestId=request_id,
        )
        target_contract, audit_report = self.get_full_report(requestor, uri, request_id)

        self.config.report_encoder.validate_json(audit_report, request_id)

        compressed_report = self.config.report_encoder.compress_report(audit_report,
                                                                         request_id)

        audit_report_str = json.dumps(audit_report, indent=2)
        audit_hash = digest(audit_report_str)

        upload_result = self.config.upload_provider.upload_report(audit_report_str,
                                                                  audit_report_hash=audit_hash)

        self.logger.info(
            "Report upload result: {0}".format(upload_result),
            requestId=request_id,
        )

        if not upload_result['success']:
            raise Exception("Error uploading {0} report: {1}".format(report_type, json.dumps(upload_result)))

        parse_uri = urllib.parse.urlparse(uri)
        original_file_name = os.path.basename(parse_uri.path)
        contract_body = read_file(target_contract)
        contract_upload_result = self.config.upload_provider.upload_contract(request_id,
                                                                             contract_body,
                                                                             original_file_name)
        if contract_upload_result['success']:
            self.logger.info(
                "Contract upload result: {0}".format(contract_upload_result),
                requestId=request_id,
            )
        else:
            # We just log on error, not raise an exception
            self.logger.error(
                "Contract upload result: {0}".format(contract_upload_result),
                requestId=request_id,
            )

        return {
            'audit_state': audit_report['audit_state'],
            'audit_uri': upload_result['url'],
            'audit_hash': audit_hash,
            'full_report': json.dumps(audit_report),
            'compressed_report': compressed_report,
        }

    def __process_audit_request(self, evt):
        request_id = None
        report_type = "unknown"
        try:
            requestor = evt['requestor']
            request_id = evt['request_id']
            contract_uri = evt['contract_uri']

            report_type = "police" if is_police_check(evt) else "audit"
            audit_result = self.audit(requestor, contract_uri, request_id, report_type)

            if audit_result is None:
                error = "Could not generate {0} report".format(report_type)
                evt['status_info'] = error
                evt['compressed_report'] = PerformAuditThread.__EMPTY_COMPRESSED_REPORT
                self.logger.exception(error, requestId=request_id)
                self.config.event_pool_manager.set_evt_to_error(evt)
            else:
                evt['audit_uri'] = audit_result['audit_uri']
                evt['audit_hash'] = audit_result['audit_hash']
                evt['audit_state'] = audit_result['audit_state']
                evt['full_report'] = audit_result['full_report']
                evt['compressed_report'] = audit_result['compressed_report']
                evt['submission_block_nbr'] = self.config.web3_client.eth.blockNumber
                evt['status_info'] = "Successfully generated report"
                msg = "Generated report URI is {0}. Saving it in the internal database " \
                      "(if not previously saved)"
                self.logger.debug(
                    msg.format(str(evt['audit_uri'])), requestId=request_id, evt=evt
                )
                self.config.event_pool_manager.set_evt_status_to_be_submitted(evt)
        except KeyError as error:
            self.logger.exception(
                "KeyError when trying to produce {0} report from request event {1}: {2}".format(report_type, evt,
                                                                                                error),
                requestId=request_id
            )
        except Exception as error:
            self.logger.exception(
                "Error when trying to produce {0} report from request event {1}: {2}".format(report_type, evt, error),
                requestId=request_id,
            )
            evt['status_info'] = traceback.format_exc()
            self.config.event_pool_manager.set_evt_status_to_error(evt)

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        TimeIntervalPollingThread.__init__(
            self,
            config=config,
            target_function=self.__process_incoming,
            thread_name="audit thread"
        )
