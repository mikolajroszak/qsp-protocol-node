"""
Provides the QSP Audit node implementation.
"""
import os
import json
import utils.logging as logging_utils
import traceback

from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from time import sleep
from hashlib import sha256
from utils.io import fetch_file, digest
from utils.args import replace_args
from threading import Thread

logging = logging_utils.getLogging()

class QSPAuditNode:

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__config = config
        self.__exec = False

        start_block = self.__config.event_pool_manager.get_next_block_number()
        self.__evt_audit_request = "LogAuditRequested"
        self.__filter_audit_requests = self.__config.internal_contract.on(
            self.__evt_audit_request,
            filter_params={'fromBlock': start_block},
        )
        self.__evt_audit_submission = "LogReportSubmitted"
        self.__filter_audit_submissions = self.__config.internal_contract.on(
            self.__evt_audit_submission,
            filter_params={'fromBlock': start_block},
        )
        self.__threads = []

    def run(self):
        """
        Starts all the threads processing different stages of a given event.
        """
        self.__exec = True
        self.__run_polling_thread()
        self.__run_audit_thread()
        self.__run_submission_thread()
        self.__run_monitor_submisson_thread()

    def __run_polling_thread(self):
        def exec():
            while self.__exec:
                try:
                    evts = self.__filter_audit_requests.get()

                    if evts == []:
                        sleep(self.__config.evt_polling)
                        continue

                    logging.debug("Found incomming audit events: {0}".format(
                        str(evts)
                    ))
                except Exception as e:
                    logging.exception(
                        "Unexpected error when performing polling: {0}".format(str(e))
                    )
                    pass

                # Process all incoming events
                for evt in evts:
                    try:
                        # Accepts all events whose audit reward is at least as
                        # high as given by min_reward
                        price = evt['args']['price']
                        request_id = evt['args']['requestId']

                        if price >= self.__config.min_price:
                            logging.debug("Accepted processing audit event: {0}".format(
                                str(evt)
                            ))

                            audit_evt = {
                                'request_id': request_id,
                                'requestor': str(evt['args']['requestor']),
                                'contract_uri': str(evt['args']['uri']),
                                'evt_name': self.__evt_audit_request,
                                'block_nbr': evt['blockNumber'],
                                'status_info': "Audit request received",
                            }

                            self.__config.event_pool_manager.add_evt_to_be_processed(
                                audit_evt
                            )
                        else:
                            logging.debug(
                                "Declining processing audit request: {0}. Not enough incentive".format(
                                    str(evt)
                                ), 
                                requestId=str(request_id),
                            )
                    except Exception:
                        logging.exception(
                            "Unexpected error when receiving event {0}".format(str(evt)), 
                            requestId=str(request_id),
                        )
                        pass

        polling_thread = Thread(target=exec, name="polling thread")
        self.__threads.append(polling_thread)
        polling_thread.start()

    def __run_audit_thread(self):
        def process_audit_request(evt):
            try:
                requestor = evt['requestor']
                request_id = evt['request_id']
                contract_uri = evt['contract_uri']
                report = self.audit(requestor, contract_uri, request_id)

                if report is None:
                    error = "Could not generate report"
                    evt['status_info'] = error
                    logging.exception(error, requestId=str(request_id))
                    self.__config.event_pool_manager.set_evt_to_error(evt)
                else:
                    evt['report'] = json.dumps(report)
                    evt['status_info'] = "Sucessfully generated report"
                    logging.debug(
                        "Generated report is {0}. Saving it in the internal database".format(
                            str(evt['report']),
                            requestId=str(request_id),
                        )
                    )
                    self.__config.event_pool_manager.set_evt_to_be_submitted(evt)
            except Exception:
                logging.exception(
                    "Unexpected error when performing audit", 
                    requestId=str(request_id),
                )
                evt['status_info'] = traceback.format_exc()
                self.__config.event_pool_manager.set_evt_to_error(evt)
                pass

        def exec():
            while self.__exec:
                self.__config.event_pool_manager.process_incoming_events(
                    process_audit_request
                )
                sleep(self.__config.evt_polling)

        audit_thread = Thread(target=exec, name="audit thread")
        self.__threads.append(audit_thread)
        audit_thread.start()

    def __run_submission_thread(self):
        def process_submission_request(evt):
            try:
                tx_hash = self.__submitReport(
                    evt['request_id'],
                    evt['requestor'],
                    evt['contract_uri'],
                    evt['report'],
                )
                evt['tx_hash'] = tx_hash
                evt['status_info'] = 'Report successfully submitted'
                self.__config.event_pool_manager.set_evt_to_submitted(evt)
            except Exception:
                evt['status_info'] = traceback.format_exc()
                self.__config.event_pool_manager.set_evt_to_error(evt)

        def exec():
            while self.__exec:
                self.__config.event_pool_manager.process_events_to_be_submitted(
                    process_submission_request
                )

                sleep(self.__config.evt_polling)

        submission_thread = Thread(target=exec, name="submission thread")
        self.__threads.append(submission_thread)
        submission_thread.start()


    def __run_monitor_submisson_thread(self):
        timeout_limit=self.__config.submission_timeout_limit

        def monitor_submission_timeout(evt, current_block):
            if (current_block - evt['block_nbr']) > timeout_limit:
                evt['status_info'] = "Submission timeout"
                self.__config.event_pool_manager.set_evt_to_error(evt)

            # TODO How to inform the network of a submission timeout?

        def exec():
            while self.__exec:
                evts = self.__filter_audit_submissions.get()

                # Processes the current event batch
                if evts != []:
                    for evt in evts:
                        request_id = str(evt['args']['requestId'])
                        audit_evt = self.__config.event_pool_manager.fetch_evt(
                            request_id
                        )
                        if audit_evt is not None:
                            self.__config.event_pool_manager.set_evt_as_submitted(
                                audit_evt
                            )

                # Checks for a potential timeouts
                block = self.__config.web3_client.eth.blockNumber
                self.__config.event_pool_manager.process_submission_events(
                    monitor_submission_timeout,
                    block,
                )

                sleep(self.__config.evt_polling)

        monitor_thread = Thread(target=exec, name="monitor thread")
        self.__threads.append(monitor_thread)
        monitor_thread.start()

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec = False
        for thread in self.__threads:
            thread.join()

        self.__threads = []

    def audit(self, requestor, uri, request_id):
        """
        Audits a target contract.
        """
        logging.info(
            "Executing audit on contract at {0}".format(uri), 
            requestId=str(request_id),
        )

        target_contract = fetch_file(uri)

        report = self.__config.analyzer.check(
            target_contract,
            self.__config.analyzer_output,
            request_id,
        )
        
        report_as_string = str(json.dumps(report))
        
        upload_result = self.__config.report_uploader.upload(report_as_string)
        logging.info(
            "Report upload result: {0}".format(upload_result), requestId=str(request_id))
        
        if (upload_result['success'] is False):
          raise Exception("Unexpected error when uploading report: {0}".format(json.dumps(upload_result)), requestId=request_id)

        report_as_string = str(json.dumps(report))

        upload_result = self.__config.report_uploader.upload(report_as_string)

        logging.info(
            "Report upload result: {0}".format(upload_result), 
            requestId=str(request_id),
        )

        if not upload_result['success']:
            raise Exception("Error uploading report: {0}".format(json.dumps(upload_result)))

        return {
            'auditor': self.__config.account,
            'requestor': str(requestor),
            'contract_uri': str(uri),
            'contract_sha256': str(digest(target_contract)),
            'report_uri': upload_result['url'],
            'report_sha256': sha256(report_as_string.encode()).hexdigest(),
            'timestamp': str(datetime.utcnow()),
        }

    def __submitReport(self, request_id, requestor, contract_uri, report):
        """
        Submits the audit report to the entire QSP network.
        """
        gas = self.__config.default_gas

        if gas is None:
            args={'from': self.__config.account}
        else:
            args={'from': self.__config.account, 'gas': int(gas)}

        self.__config.wallet_session_manager.unlock(self.__config.account_ttl)
        return self.__config.internal_contract.transact(args).submitReport(
            request_id,
            requestor,
            contract_uri,
            report,
        )
