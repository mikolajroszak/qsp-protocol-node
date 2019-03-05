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

from log_streaming import get_logger

from .threads import ClaimRewardsThread
from .threads import CollectMetricsThread, ComputeGasPriceThread, PollRequestsThread
from .threads import UpdateMinPriceThread, QSPThread, SubmitReportThread, PerformAuditThread
from .threads import MonitorSubmissionThread
from utils.eth import mk_read_only_call


class QSPAuditNode:

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
        #    RQ (Requested) < AS (Assigned) < TS (To be submitted) < SB (Submitted) < DN (Done)
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

    @staticmethod
    def is_police_officer(config):
        """
        Verifies whether the node is a police node.
        """
        is_police = False
        try:
            is_police = mk_read_only_call(
                config,
                config.audit_contract.functions.isPoliceNode(config.account))
        except Exception as err:
            config.logger.debug("Failed to check if node is a police officer: {0}".format(err))
            config.logger.debug("Assuming the node is not a police officer.")

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

    def __start_poll_requests_thread(self):
        """
        Creates and starts the poll requests thread. Appends the handle to the internal threads.
        """
        poll_requests_thread = PollRequestsThread(self.config)
        self.__internal_thread_definitions.append(poll_requests_thread)
        handle = poll_requests_thread.start()
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

        self.__start_poll_requests_thread()

        # Starts two additional threads for performing audits
        # and eventually submitting results
        self.__internal_thread_handles.append(self.__start_submission_thread())
        self.__start_perform_audit_thread()
        self.__start_monitor_submisson_thread()

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

    def __start_claim_rewards_thread(self):
        """
        Collects any unclaimed audit rewards every 24 hours.
        """
        claim_rewards_thread = ClaimRewardsThread(self.config)
        self.__internal_thread_definitions.append(claim_rewards_thread)
        handle = claim_rewards_thread.start()
        self.__internal_thread_handles.append(handle)
        return handle

    def __start_monitor_submisson_thread(self):
        monitor_thread = MonitorSubmissionThread(self.__config)
        self.__internal_thread_definitions.append(monitor_thread)
        handle = monitor_thread.start()
        self.__internal_thread_handles.append(handle)

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

    @property
    def is_initialized(self):
        return self.__is_initialized
