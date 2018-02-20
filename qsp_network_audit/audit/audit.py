"""
Provides the QSP Audit node implementation.
"""
from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from time import sleep
import os
import json
import logging

from utils.io import fetch_file, digest
from utils.args import replace_args
from threading import Thread


class QSPAuditNode:

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__config = config
        self.__exec = False
        self.__beep = self.__config.event_pool_manager.get_next_beep()

        start_block = self.__config.event_pool_manager.get_next_block_number()
        self.__evt_audit_requests = "LogAuditRequested"
        self.__filter_audit_requests = self.__config.internal_contract.on(
            self.__evt_audit_requests,
            filter_params={'fromBlock': start_block},
        )
        self.__evt_audit_submissions = "LogAuditSubmitted"
        self.__filter_audit_submissions = self.__config.internal_contract.on(
            self.__evt_audit_submissions,
            filter_params={'fromBlock': start_block},
        )

    def run(self):
        """
        Starts all the threads processing different stages of a given event.
        """
        self.__exec = True
        self.__run_polling_thread()
        self.__run_audit_thread()
        self.__run_submission_thread()
        self.__run_check_submisson_thread()

    def __run_polling_thread(self):
        def exec():
            while self.__exec:
                evts = self.__filter_audit_requests.get()

                if evts == []:
                    sleep(self.__config.evt_polling)
                    continue

                logging.debug("Found incomming audit events: {0}".format(
                    str(evts)
                ))

                # Process all incoming events
                for evt in evts:

                    # Accepts all events whose audit reward is at least as
                    # high as given by min_reward
                    price = evt['args']['price']
                    request_id = str(evt['args']['requestId'])

                    if price >= self.__config.min_price:
                        logging.debug("Accepted processing audit event: {0}".format(
                            str(evt)
                        ))

                        audit_evt = {
                            'request_id': request_id,
                            'requestor': str(evt['args']['requestor']),
                            'contract_uri': str(evt['args']['uri']),
                            'beep': self.__beep,
                            'evt_name': self.__evt_audit_requests,
                            'block_number': evt['blockNumber'],
                        }

                        self.__config.event_pool_manager.add_evt_to_be_processed(
                            audit_evt)
                    else:
                        logging.debug(
                            "Declining processing audit request: {0}. Not enough incentive".format(
                                str(evt)
                            ), requestId=request_id
                        )

        Thread(target=exec, name="QSP_audit_node: polling_thread").start()

    def __run_audit_thread(self):
        def process_audit_request(evt):
            try:
                requestor = evt['requestor']
                request_id = evt['request_id']
                contract_uri = evt['contract_uri']
                report = self.audit(requestor, contract_uri, request_id)

                if report is None:
                    logging.exception(
                        "Could not generate report", requestId=request_id)
                    self.__config.event_pool_manager.set_evt_to_error(evt)
                else:
                    evt['report'] = json.dumps(report)
                    logging.debug(
                        "Generated report is {0}. Saving it in the internal database".format(str(evt['report']),
                        requestId=request_id)
                self.__config.event_pool_manager.set_evt_to_be_submitted(evt)
            except Exception:
                logging.exception(
                    "Unexpected error when performing audit", requestId=request_id)
                self.__config.event_pool_manager.set_evt_to_error(evt)
                pass

        def exec():
            while self.__exec:
                self.__config.event_pool_manager.process_incoming_events(
                    process_audit_request)

                sleep(self.__config.evt_polling)

        Thread(target=exec, name="QSP_audit_node: audit_thread").start()

    def __run_submission_thread(self):
        def process_submission_request(evt):
            try:
                tx_hash=self.__submitReport(
                    evt['request_id'],
                    evt['requestor'],
                    evt['contract_uri'],
                    evt['report'],
                )
                evt['tx_hash']=tx_hash
                self.__config.record_submission(evt)
            except Exception:
                self.__config.set_evt_to_error(evt)

        def exec():
            while self.__exec:
                self.__config.event_pool_manager.process_events_to_be_submitted(
                    process_submission_request)

                sleep(self.__config.evt_polling)

        Thread(target=exec, name="QSP_audit_node: submission_thread").start()


    def __run_monitor_submisson_thread(self):
        def monitor_evt(evt):

        def exec():
            while self.__exec:
                evts=self.__filter_audit_submissions.get()

                # Processes the current event batch
                if evts != []:
                    for evt in evts:
                        request_id=str(evt['args']['requestId'])
                        audit_evt=self.__config.event_pool_manager.fetch_evt(
                            request_id)
                        if audit_evt is not None:
                            self.__config.event_pool_manager.set_evt_as_submitted(
                                audit_event
                            )
                else:
                    # If there are no events, then check for a potential timeout
                    block=self.__config.web3client.eth.blockNumber
                    self.__config.event_pool_manager.process_events_to_be_monitored(
                        monitor_evt, block
                    )

                sleep(self.__config.evt_polling)








    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec=False

    def audit(self, requestor, uri, request_id):
        """
        Audits a target contract.
        """
        logging.info("Executing audit on contract at {0}".format(
            uri), requestId=request_id)

        target_contract=fetch_file(uri)

        report=self.__config.analyzer.check(
            target_contract,
            self.__config.analyzer_output,
            request_id
        )

        report_as_string=str(json.dumps(report))

        upload_result=self.__config.report_uploader.upload(report_as_string)
        logging.info(
            "Report upload result: {0}".format(upload_result), requestId=request_id)

        if not upload_result['success']:
            logging.exception(
                "Unexpected error when uploading report: {0}".format(json.dumps(upload_result)), requestId=request_id)
            return None

        return {
            'auditor': self.__config.account,
            'requestor': str(requestor),
            'contract_uri': str(uri),
            'contract_sha256': str(digest(target_contract)),
            'report_uri': upload_result['url'],
            'report_sha256': sha256(report_as_string.encode()).hexdigest(),
            'timestamp': str(datetime.utcnow()),
        }

    def __submitReport(self, requestor, contract_uri, report):
        """
        Submits the audit report to the entire QSP network.
        """
        gas=self.__config.default_gas

        if gas is None:
            args={'from': self.__config.account}
        else:
            args={'from': self.__config.account, 'gas': int(gas)}

        self.__config.wallet_session_manager.unlock(self.__config.account_ttl)
        return self.__config.internal_contract.transact(args).submitReport(
            requestor,
            contract_uri,
            report,
        )
