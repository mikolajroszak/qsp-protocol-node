"""
Provides the QSP Audit node implementation.
"""
import json
import utils.logging as logging_utils
import traceback

from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from time import sleep
from hashlib import sha256
from utils.io import fetch_file, digest
from utils.eth import mk_args
from threading import Thread
from utils.eth import FilterThreads

logger = logging_utils.get_logger()


class QSPAuditNode:

    __EVT_AUDIT_REQUESTED = "LogAuditQueued"
    __EVT_AUDIT_REQUEST_ASSIGNED = "LogAuditRequestAssigned"
    __EVT_REPORT_SUBMITTED = "LogReportSubmitted"

    # must be in sync with https://github.com/quantstamp/qsp-network-contract-interface/blob/4381a01f8714efe125699b047e8348e9e2f2a243/contracts/QuantstampAudit.sol#L16
    __AUDIT_STATE_SUCCESS = 4

    # must be in sync with https://github.com/quantstamp/qsp-network-contract-interface/blob/4381a01f8714efe125699b047e8348e9e2f2a243/contracts/QuantstampAudit.sol#L17
    __AUDIT_STATE_ERROR = 5

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__config = config
        self.__exec = False

        start_block = self.__config.event_pool_manager.get_latest_block_number()

        # If no block has currently been processed, start from zero
        if start_block == -1:
            start_block = 0

        logger.debug("Filtering events from block # {0}".format(str(start_block)))

        # There are some important invariants that are to be respected at all
        # times when the audit node (re-)processes events (see associated queries):
        #
        # 1) An audit event is never saved twice in the node's internal database
        #
        # 2) If an event has been given a certain status, it is never
        #    updated with a status lower in ranking
        #    The current ranking is given by:
        #   
        #    RV (Received) < TS (To be submitted) < SB (submitted) < DN (done)
        #
        # 3) Errors are currently not recoverable, i.e., if an audit event reaches
        #    an error state in the finite automata internally captured by the audit node,
        #    the event never leaves that state
        #
        # 4) At all times, there is at most one writer thread executing. Stated otherwise,
        #    concurrent writes never occurs
        #
        # 5) At all times, the audit node only accounts for the health of threads
        #    processing new events. Old ones necessarily cause the underlying
        #    thread to complete execution and eventually dying

        params = {'fromBlock': start_block}

        self.__set_filter(QSPAuditNode.__EVT_AUDIT_REQUESTED, params, self.__on_audit_requested)
        self.__set_filter(QSPAuditNode.__EVT_AUDIT_REQUEST_ASSIGNED, params, self.__on_audit_assigned)
        self.__set_filter(QSPAuditNode.__EVT_REPORT_SUBMITTED, params, self.__on_report_submitted)

        self.__latest_request_id = self.__config.event_pool_manager.get_latest_request_id()
        self.__internal_threads = []

    def __set_filter(self, evt_name, params, callback):
        self.__config.internal_contract.pastEvents(evt_name, params, callback)
        FilterThreads.register(self.__config.internal_contract.on(evt_name, params, callback))

    @property
    def config(self):
        return self.__config

    def run(self):
        """
        Starts all the threads processing different stages of a given event.
        """
        if self.__exec:
            raise Exception("Cannot run audit node thread due to another audit node instance")

        self.__exec = True

        # Starts two additional threads for performing audits
        # and eventually submitting results
        self.__internal_threads.append(self.__run_perform_audit_thread())
        self.__internal_threads.append(self.__run_submission_thread())
        self.__internal_threads.append(self.__run_monitor_submisson_thread())

        # Monitors the state of each thread. Upon error, terminate the
        # audit node. Checking whether a thread is alive or not does
        # not account for pastEvent threads, which necessarily die
        # after processing them all.

        health_check_interval_sec = 2
        while self.__exec:
            # Checking if all threads are still alive
            for thread in (self.__internal_threads + FilterThreads.list()):
                if not thread.is_alive():
                    logger.debug("Cannot proceed execution. At least one internal thread is lost")
                    self.stop()

            # Specifically check the state of filter threads
            # (may be executing, but not able to filter anything)
            for filter_thread in FilterThreads.list():
                if not FilterThreads.is_alive(filter_thread):
                    logger.debug("Cannot proceed execution. At least one filter id was lost")
                    self.stop()

            sleep(health_check_interval_sec)


    def __on_audit_requested(self, evt):
        """
        Bids for an audit upon an audit request event.
        """
        try:
            # Bids for audit requests whose reward is at least as
            # high as given by the configured min_price
            price = evt['args']['price']
            request_id = str(evt['args']['requestId'])

            if (price >= self.__config.min_price):
                logger.debug("Accepted processing audit event: {0}. Bidding for it (if not already done so)".format(
                    str(evt)), requestId=request_id)
                self.__get_next_audit_request()

            else:
                logger.debug(
                    "Declining processing audit request: {0}. Not enough incentive".format(
                        str(evt)
                    ),
                    requestId=request_id,
                )
        except Exception as error:
            logger.exception(
                "Error when processing audit request event {0}: {1}".format(str(evt), str(error)),
                requestId=request_id,
            )

    def __on_audit_assigned(self, evt):
        request_id = str(evt['args']['requestId'])
        try:
            target_auditor = evt['args']['auditor']

            # If an audit request is not targeted to the
            # running audit node, just disconsider it
            if target_auditor.lower() != self.__config.account.lower():
                logger.debug(
                    "Ignoring audit request (not directed at current node): {0}".format(
                        str(evt)
                    ),
                    requestId=request_id,
                )
                return

            logger.debug(
                "Saving audit request for processing (if new): {0}".format(
                    str(evt)
                ),
                requestId=request_id,
            )

            # Otherwise, the audit request must be processed
            # throught its different stages. As such, save it
            # in the internal database, marking it as RECEIVED

            audit_evt = {
                'request_id': request_id,
                'requestor': str(evt['args']['requestor']),
                'contract_uri': str(evt['args']['uri']),
                'evt_name':  QSPAuditNode.__EVT_AUDIT_REQUEST_ASSIGNED,
                'block_nbr': evt['blockNumber'],
                'price': evt['args']['price'],
                'status_info': "Audit request received",
            }

            self.__config.event_pool_manager.add_evt_to_be_processed(
                audit_evt
            )
        except Exception as error:
            logger.exception(
                "Error when processing audit assigned event {0}: {1}".format(str(evt), str(error)),
                requestId=request_id,
            )

    def __on_report_submitted(self, evt):
        try:
            request_id = str(evt['args']['requestId'])
            target_auditor = evt['args']['auditor']

            # If an audit request is not targeted to the
            # running audit node, just disconsider it
            if target_auditor.lower() != self.__config.account.lower():
                logger.debug(
                    "Ignoring submission event (not directed at current node): {0}".format(
                        str(evt)
                    ),
                    requestId=request_id,
                )
                return

            audit_evt = self.__config.event_pool_manager.get_event_by_request_id(
                request_id
            )
            if audit_evt != {}:
                audit_evt['status_info'] = 'Report successfully submitted'
                self.__config.event_pool_manager.set_evt_to_done(
                    audit_evt
                )
        except Exception as error:
            logger.exception(
                "Error when processing submission event {0}: {1}. Audit event is {2}".format(
                    str(evt),
                    str(error),
                    str(audit_evt),
                ),
                requestId=request_id,
            )

    def __run_perform_audit_thread(self):
        def process_audit_request(evt):
            try:
                requestor = evt['requestor']
                request_id = evt['request_id']
                contract_uri = evt['contract_uri']
                audit_result = self.audit(requestor, contract_uri, request_id)

                if audit_result is None:
                    error = "Could not generate report"
                    evt['status_info'] = error
                    logger.exception(error, requestId=request_id)
                    self.__config.event_pool_manager.set_evt_to_error(evt)
                else:
                    evt['report_uri'] = audit_result['report_uri']
                    evt['report_hash'] = audit_result['report_hash']
                    evt['audit_state'] = audit_result['audit_state']
                    evt['status_info'] = "Sucessfully generated report"
                    logger.debug(
                        "Generated report URI is {0}. Saving it in the internal database (if not previously saved)".format(
                            str(evt['report_uri'])
                        ), requestId=request_id, evt=evt
                    )
                    self.__config.event_pool_manager.set_evt_to_be_submitted(evt)
            except Exception as error:
                logger.exception(
                    "Error when performing audit for request event {0}: {1}".format(str(evt), str(error)),
                    requestId=request_id,
                )
                evt['status_info'] = traceback.format_exc()
                self.__config.event_pool_manager.set_evt_to_error(evt)

        def exec():
            while self.__exec:
                self.__config.event_pool_manager.process_incoming_events(
                    process_audit_request
                )
                sleep(self.__config.evt_polling)

        audit_thread = Thread(target=exec, name="audit thread")
        self.__internal_threads.append(audit_thread)
        audit_thread.start()

        return audit_thread

    def __run_submission_thread(self):
        def process_submission_request(evt):
            try:
                tx_hash = self.__submit_report(
                    int(evt['request_id']),
                    evt['audit_state'],
                    evt['report_uri'],
                    evt['report_hash'],
                )
                evt['tx_hash'] = tx_hash
                evt['status_info'] = 'Report submitted (waiting for confirmation)'
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
        self.__internal_threads.append(submission_thread)
        submission_thread.start()

        return submission_thread

    def __run_monitor_submisson_thread(self):
        timeout_limit = self.__config.submission_timeout_limit_blocks

        def monitor_submission_timeout(evt, current_block):
            try:
                if (current_block - evt['block_nbr']) > timeout_limit:
                    evt['status_info'] = "Submission timeout"
                    self.__config.event_pool_manager.set_evt_to_error(evt)

                # TODO How to inform the network of a submission timeout?
            except Exception as error:
                logger.exception("Unexpected error when monitoring timeout")

        def exec():
            while self.__exec:
                # Checks for a potential timeouts
                block = self.__config.web3_client.eth.blockNumber
                self.__config.event_pool_manager.process_submission_events(
                    monitor_submission_timeout,
                    block,
                )

                sleep(self.__config.evt_polling)

        monitor_thread = Thread(target=exec, name="monitor thread")
        self.__internal_threads.append(monitor_thread)
        monitor_thread.start()

        return monitor_thread

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec = False

        for internal_thread in self.__internal_threads:
            internal_thread.join()
        self.__internal_threads = []

        # Close resources
        self.__config.wallet_session_manager.lock()
        self.__config.event_pool_manager.close()

    def audit(self, requestor, uri, request_id):
        """
        Audits a target contract.
        """
        logger.info(
            "Executing audit on contract at {0}".format(uri), 
            requestId=request_id,
        )

        target_contract = fetch_file(uri)

        analyzer_report = self.__config.analyzer.check(
            target_contract,
            self.__config.analyzer_output,
            request_id,
        )
        
        logger.info(
            "Analyzer report contents",
            requestId=request_id,
            contents = analyzer_report,
        )
        
        full_report = {
          'auditor': self.__config.account,
          'requestor': str(requestor),
          'contract_uri': str(uri),
          'contract_sha256': str(digest(target_contract)),
          'analyzer_report': str(json.dumps(analyzer_report)),
          'timestamp': str(datetime.utcnow()),
        }

        report_as_string = str(json.dumps(full_report, indent=2))
        report_hash = str(sha256(report_as_string.encode()).hexdigest())
        upload_result = self.__config.report_uploader.upload(report_as_string)

        logger.info(
            "Report upload result: {0}".format(upload_result), 
            requestId=request_id,
        )

        if not upload_result['success']:
            raise Exception("Error uploading report: {0}".format(json.dumps(upload_result)))

        audit_state = QSPAuditNode.__AUDIT_STATE_SUCCESS if analyzer_report['status'] == 'success' else QSPAuditNode.__AUDIT_STATE_ERROR;

        return {
            'audit_state': audit_state,
            'report_uri': upload_result['url'],
            'report_hash': report_hash
        }

    def __get_next_audit_request(self):
        """
        Attempts to get a request from the audit request queue.
        """
        tx_args = mk_args(self.__config)
        self.__config.wallet_session_manager.unlock(self.__config.account_ttl)
        return self.__config.internal_contract.transact(tx_args).getNextAuditRequest() 

    def __submit_report(self, request_id, audit_state, report_uri, report_hash):
        """
        Submits the audit report to the entire QSP network.
        """
        tx_args = mk_args(self.__config)
        self.__config.wallet_session_manager.unlock(self.__config.account_ttl)
        return self.__config.internal_contract.transact(tx_args).submitReport(
            request_id,
            audit_state,
            report_uri,
            report_hash
        )
