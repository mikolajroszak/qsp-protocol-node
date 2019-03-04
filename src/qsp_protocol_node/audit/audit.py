####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the QSP Audit node implementation.
"""

from evt import set_evt_as_audit
from evt import set_evt_as_police_check
from log_streaming import get_logger
from utils.eth.tx import TransactionNotConfirmedException
from web3.utils.threads import Timeout

from .exceptions import NotEnoughStake
from .threads import ClaimRewardsThread
from .threads import CollectMetricsThread, ComputeGasPriceThread
from .threads import UpdateMinPriceThread, QSPThread, SubmitReportThread, PerformAuditThread
from utils.eth import send_signed_transaction
from utils.eth import mk_read_only_call
from utils.eth import DeduplicationException

from threading import Thread


class QSPAuditNode:
    __EVT_AUDIT_ASSIGNED = "LogAuditAssigned"
    __EVT_REPORT_SUBMITTED = "LogAuditFinished"

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAudit.sol#L106
    __AVAILABLE_AUDIT_STATE_READY = 1

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAudit.sol#L110
    __AVAILABLE_AUDIT_UNDERSTAKED = 5

    # The frequency of updating min price. This is not configurable as dashboard logic depends
    # on this frequency
    __MIN_PRICE_BEAT_SEC = 24 * 60 * 60

    # Empty report for certain error cases
    __EMPTY_COMPRESSED_REPORT = ""

    # Similarity threshold to deem a report correct
    __SIMILARITY_THRESHOLD = .6

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__config = config
        self.__exec = False
        self.__internal_thread_handles = []
        self.__internal_thread_definitions = []
        self.__is_initialized = False

        # There are some important invariants that are to be respected at all
        # times when the audit node (re-)processes events (see associated queries):
        #
        # 1) An audit event is never saved twice in the node's internal database
        #
        # 2) If an event has been given a certain status, it is never
        #    updated with a status lower in ranking
        #    The current ranking is given by:
        #
        #    RQ (Requested) < AS (Assigned < TS (To be submitted) < SB (Submitted) < DN (Done)
        #
        # 3) Errors are currently not recoverable, i.e., if an audit event reaches
        #    an error state in the finite automata internally captured by the audit node,
        #    the event never leaves that state
        #
        # 4) At all times, there is at most one writer thread executing. Stated otherwise,
        #    concurrent writes never occur
        #
        # 5) At all times, the audit node only accounts for the health of threads
        #    processing new events. Old ones necessarily cause the underlying
        #    thread to complete execution and eventually dying

    def __run_with_interval(self, body_function, polling_interval, start_with_call=True):
        # todo(mderka): QSP-1023
        # todo(mderka): This method was moved to QSPThread. For now, we only delegate the call.
        # todo(mderka): Remove this method completely from here when the refactoring is complete
        # todo(mderka): and it is no longer necessary.
        wrapper = QSPThread(self.config)
        self.__internal_thread_definitions.append(wrapper)
        return wrapper.run_with_interval(body_function, polling_interval,
                                         start_with_call=start_with_call)

    def __run_block_mined_thread(self, handler_name, handler):
        """
        Checks if a new block is mined. Reacting to a new block the handler is called.
        """
        # todo(mderka): QSP-1023
        # todo(mderka): This method was moved to QSPThread. For now, we only delegate the call.
        # todo(mderka): Remove this method completely from here when the refactoring is complete
        # todo(mderka): and it is no longer necessary.
        wrapper = QSPThread(self.config)
        self.__internal_thread_definitions.append(wrapper)
        return wrapper.run_block_mined_thread(handler_name, handler)

    @property
    def config(self):
        return self.__config

    def __has_enough_stake(self):
        """
        Verifies whether the node has enough stake to perform audits.
        """
        enough_stake = False
        try:
            enough_stake = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.hasEnoughStake(self.config.account))
        except Exception as err:
            raise err

        return enough_stake

    def __get_min_stake_qsp(self):
        """
        Gets the minimum staking (in QSP) required to perform an audit.
        """
        min_stake = mk_read_only_call(
            self.config,
            self.config.audit_contract.functions.getMinAuditStake())

        # Puts the result (wei-QSP) back to QSP
        return min_stake / (10 ** 18)

    def is_police_officer(self):
        """
        Verifies whether the node is a police node.
        """
        is_police = False
        try:
            is_police = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.isPoliceNode(self.config.account))
        except Exception as err:
            self.__logger.debug("Failed to check if node is a police officer: {0}".format(err))
            self.__logger.debug("Assuming the node is not a police officer.")

        return is_police

    def __start_gas_price_thread(self):
        """
        Creates and starts the gas price thread. Appends the handle to the internal threads.
        """
        gas_price_thread = ComputeGasPriceThread(self.config)
        self.__internal_thread_definitions.append(gas_price_thread)

        # Immediately compute gas price once upon startup
        gas_price_thread.compute_gas_price()

        handle = gas_price_thread.start()
        self.__internal_thread_handles.append(handle)

    def __start_submission_thread(self):
        submission_thread = SubmitReportThread(self.config)
        self.__internal_thread_definitions.append(submission_thread)
        return submission_thread.start()

    def __start_min_price_thread(self):
        """
        Creates and starts the min price thread. Appends the handle to the internal threads.
        """
        min_price_thread = UpdateMinPriceThread(self.config)
        self.__internal_thread_definitions.append(min_price_thread)
        if self.config.heartbeat_allowed:
            # Updates min price and starts a thread that will be doing so every 24 hours
            min_price_thread.update_min_price()
            # Starts the thread and keeps the handle
            handle = min_price_thread.start()
            self.__internal_thread_handles.append(handle)

        else:
            # Updates min price only if it differs
            min_price_thread.check_and_update_min_price()

    def __start_metric_collection_thread(self):
        """
        Creates and starts the metric collection thread. Appends the handle to the internal threads.
        """
        if self.__config.metric_collection_is_enabled:
            metric_collection_thread = CollectMetricsThread(self.config)
            self.__internal_thread_definitions.append(metric_collection_thread)

            # Collect initial metrics
            metric_collection_thread.collect_and_send()

            # Starts the thread and keeps the handle
            handle = metric_collection_thread.start()
            self.__internal_thread_handles.append(handle)

    def __start_perform_audit_thread(self):
        """
        Creates and starts the min price thread. Appends the handle to the internal threads.
        """
        audit_thread = PerformAuditThread(self.config)
        self.__internal_thread_definitions.append(audit_thread)

        # Starts the thread and keeps the handle
        handle = audit_thread.start()
        self.__internal_thread_handles.append(handle)

    def run(self):
        """
        Starts all the threads processing different stages of a given event.
        """
        if self.__exec:
            raise Exception("Cannot run audit node thread due to another audit node thread instance")

        self.__exec = True
        self.__start_gas_price_thread()
        self.__start_min_price_thread()
        # Collect any unclaimed rewards every 24 hours
        self.__start_claim_rewards_thread()

        self.__start_metric_collection_thread()

        # Upon restart, before processing, set all events that timed out to err
        self.__timeout_stale_requests()

        # If no block has currently been processed, start from the current block
        # Note: this default behavior will prevent the node from finding existing audit transactions
        start_block = self.__config.event_pool_manager.get_latest_block_number()
        if start_block < 0:
            # the database is empty
            current_block_number = self.__config.web3_client.eth.blockNumber
            n_blocks_in_the_past = self.__config.start_n_blocks_in_the_past
            start_block = max(0, current_block_number - n_blocks_in_the_past)

        self.__logger.debug("Filtering events from block # {0}".format(str(start_block)))

        self.__internal_thread_handles.append(self.__run_block_mined_thread(
            "poll_requests",
            self.__poll_requests
        ))

        # Starts two additional threads for performing audits
        # and eventually submitting results
        self.__internal_thread_handles.append(self.__start_submission_thread())
        self.__start_perform_audit_thread()
        self.__internal_thread_handles.append(self.__run_monitor_submisson_thread())

        # Monitors the state of each thread. Upon error, terminate the
        # audit node. Checking whether a thread is alive or not does
        # not account for pastEvent threads, which necessarily die
        # after processing them all

        health_check_interval_sec = 2

        def check_all_threads():
            if not self.__exec:
                return

            thread_lost = False
            # Checking if all threads are still alive
            for thread in self.__internal_thread_handles:
                if not thread.is_alive():
                    print("!!!!")
                    print(thread)
                    thread_lost = True
                    break
            if thread_lost:
                raise Exception(
                    "Cannot proceed execution. At least one internal thread is not alive")

        self.__is_initialized = True
        self.__run_with_interval(check_all_threads, health_check_interval_sec)

    def __timeout_stale_requests(self):
        first_valid_block = self.__config.web3_client.eth.blockNumber - \
                            self.__config.submission_timeout_limit_blocks + \
                            self.__config.block_discard_on_restart

        def timeout_event(evt):
            try:
                if first_valid_block >= evt['block_nbr']:
                    evt['status_info'] = "Submission timeout"
                    self.__config.event_pool_manager.set_evt_status_to_error(evt)
            except KeyError as error:
                self.__logger.exception(
                    "KeyError when handling timeout on restart: {0}".format(str(error))
                )
            except Exception as error:
                self.__logger.exception(
                    "Unexpected error when handling timeout on restart: {0}".format(error))

        self.__config.event_pool_manager.process_incoming_events(timeout_event)
        self.__config.event_pool_manager.process_events_to_be_submitted(timeout_event)

    def __poll_requests(self):
        """
        Polls the audit contract for any possible requests.
        """
        self.__poll_audit_request()
        self.__poll_police_request()

    def __poll_audit_request(self):
        """
        Checks first an audit is assignable; then, bids to get an audit request.
        If successful, save the event in the database to move it along the audit pipeline.
        """
        try:
            most_recent_audit = mk_read_only_call(
                self.config,
                self.__config.audit_contract.functions.myMostRecentAssignedAudit()
            )
            request_id = most_recent_audit[0]

            # Checks if a previous bid was won. If so, it saves the event to the
            # database for processing by other threads and continues bidding
            # upon an available request

            new_assigned_request = (request_id != 0) and not self.__config.event_pool_manager.is_request_processed(
                request_id=request_id
            )

            if new_assigned_request:
                # New request id in (bid won). Persists the event in the database
                self.__add_evt_to_db(
                    request_id=request_id,
                    requestor=most_recent_audit[1],
                    uri=most_recent_audit[2],
                    price=most_recent_audit[3],
                    block_nbr=most_recent_audit[4]
                )

            # The node should attempt to bid. Before that, though, gotta perform some checks...

            pending_requests_count = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.assignedRequestCount(self.__config.account))

            if pending_requests_count >= self.__config.max_assigned_requests:
                self.__logger.debug(
                    "Skip bidding as node is currently processing {0} requests".format(
                        str(pending_requests_count)))
                return
            any_request_available = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.anyRequestAvailable())

            if any_request_available == self.__AVAILABLE_AUDIT_UNDERSTAKED:
                raise NotEnoughStake("Missing funds. To audit contracts, nodes must stake at least {0} QSP".format(
                    self.__get_min_stake_qsp()
                ))

            if any_request_available == self.__AVAILABLE_AUDIT_STATE_READY:
                self.__logger.debug("There is request available to bid on.")

                # At this point, the node is ready to bid. As such,
                # it tries to get the next audit request
                self.__get_next_audit_request()
            else:
                self.__logger.debug(
                    "No request available as the contract returned {0}.".format(
                            str(any_request_available)))

        except NotEnoughStake as error:
            self.__logger.warning("Cannot poll for audit request: {0}".format(str(error)))

        except DeduplicationException as error:
            self.__logger.debug(
                "Error when attempting to perform an audit request: {0}".format(str(error))
            )
        except TransactionNotConfirmedException as error:
            error_msg = "A transaction occurred, but was then uncled and never recovered. {0}"
            self.__logger.debug(error_msg.format(str(error)))
        except Exception as error:
            self.__logger.exception(str(error))

    def __poll_police_request(self):
        """
        Polls the audit contract for police requests (aka assignments). If the
        node is not a police officer, do nothing. Otherwise, save the event in
        the database to move it along the audit pipeline.
        """

        if not self.is_police_officer():
            return

        try:
            probe = self.__get_next_police_assignment()
            has_assignment = probe[0]

            already_processed = self.__config.event_pool_manager.is_request_processed(
                request_id=probe[1]
            )

            # If the police node does not have an assignment
            # or has one that has been already processed, do nothing
            if already_processed or not has_assignment:
                return

            # Otherwise, save to DB
            self.__add_evt_to_db(
                request_id=probe[1],
                requestor=self.config.audit_contract_address,
                price=probe[2],
                uri=probe[3],
                block_nbr=probe[4],
                is_audit=False)
        except Exception as error:
            self.__logger.exception("Error polling police requests: {0}".format(str(error)))

    def __start_claim_rewards_thread(self):
        """
        Collects any unclaimed audit rewards every 24 hours.
        """
        claim_rewards_thread = ClaimRewardsThread(self.config)
        self.__internal_thread_definitions.append(claim_rewards_thread)
        handle = claim_rewards_thread.start()
        self.__internal_thread_handles.append(handle)
        return handle

    def __add_evt_to_db(self, request_id, requestor, uri, price, block_nbr, is_audit=True):
        evt = {}
        try:
            evt = {
                'request_id': str(request_id),
                'requestor': str(requestor),
                'contract_uri': str(uri),
                'evt_name': QSPAuditNode.__EVT_AUDIT_ASSIGNED,
                'block_nbr': str(block_nbr),
                'status_info': "Audit Assigned",
                'price': str(price),
            }
            evt = set_evt_as_audit(evt) if is_audit else set_evt_as_police_check(evt)
            self.__config.event_pool_manager.add_evt_to_be_assigned(evt)
        except KeyError as error:
            self.__logger.exception(
                "KeyError when processing audit assigned event: {0}".format(str(error))
            )
        except Exception as error:
            self.__logger.exception(
                "Error when processing audit assigned event {0}: {1}".format(str(evt), str(error)),
                requestId=request_id,
            )
            self.__config.event_pool_manager.set_evt_status_to_error(evt)

    def __get_next_police_assignment(self):
        """
        Gets the next police assignment tuple.
        """
        return mk_read_only_call(
            self.__config,
            self.__config.audit_contract.functions.getNextPoliceAssignment()
        )

    def __run_monitor_submisson_thread(self):
        timeout_limit = self.__config.submission_timeout_limit_blocks

        def monitor_submission_timeout(evt, current_block):
            try:
                if (current_block - evt['block_nbr']) > timeout_limit:
                    evt['status_info'] = "Submission timeout"
                    self.__config.event_pool_manager.set_evt_status_to_error(evt)
                    msg = "Submission timeout for audit {0}. Setting to error"
                    self.__logger.debug(msg.format(str(evt['request_id'])))
            except KeyError as error:
                self.__logger.exception(
                    "KeyError when monitoring timeout: {0}".format(str(error))
                )
            except Exception as error:
                # TODO How to inform the network of a submission timeout?
                self.__logger.exception(
                    "Unexpected error when monitoring timeout: {0}".format(error))

        def process_submissions():
            # Checks for a potential timeouts
            block = self.__config.web3_client.eth.blockNumber
            self.__config.event_pool_manager.process_submission_events(
                monitor_submission_timeout,
                block,
            )

        def exec():
            try:
                self.__run_with_interval(process_submissions, self.__config.evt_polling)
            except Exception as error:
                self.__logger.exception("Error in the monitor thread: {0}".format(str(error)))

        monitor_thread = Thread(target=exec, name="monitor thread")
        self.__internal_thread_handles.append(monitor_thread)
        monitor_thread.start()

        return monitor_thread

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """

        self.__logger.info("Stopping QSP Audit Node")
        self.__exec = False

        # indicate to every thread that it should stop its execution
        for internal_thread in self.__internal_thread_definitions:
            self.__logger.debug("Thread {0} is signaled to stop.".format(internal_thread.thread_name))
            internal_thread.stop()

        # join every thread
        for internal_thread in self.__internal_thread_handles:
            internal_thread.join()
            self.__logger.debug("Thread {0} is stopped.".format(internal_thread.name))

        self.__internal_thread_handles = []

        # Close resources
        self.__config.event_pool_manager.close()

    def __get_next_audit_request(self):
        """
        Attempts to get a request from the audit request queue.
        """
        # NOTE
        # The audit contract checks whether the node has enough stake before
        # accepting a bid. No need to replicate that logic here.
        transaction = self.__config.audit_contract.functions.getNextAuditRequest()
        tx_hash = None
        try:
            tx_hash = send_signed_transaction(
                self.__config,
                transaction,
                wait_for_transaction_receipt=True)
            self.__logger.debug("A getNextAuditRequest transaction has been sent")
        except Timeout as e:
            self.__logger.debug("Transaction receipt timeout happened for {0}. {1}".format(
                str(transaction),
                e))
        return tx_hash

    @property
    def is_initialized(self):
        return self.__is_initialized
