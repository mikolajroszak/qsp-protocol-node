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

from .threads import ClaimRewardsThread
from .threads import CollectMetricsThread, ComputeGasPriceThread, PollRequestsThread
from .threads import UpdateMinPriceThread, QSPThread, SubmitReportThread, PerformAuditThread
from .threads import MonitorSubmissionThread
from utils.eth import mk_read_only_call

"""
The main QSP audit node thread.

There are some important invariants that are to be respected at all
        times when the audit node (re-)processes events (see associated queries):

        1) An audit event is never saved twice in the node's internal database

        2) If an event has been given a certain status, it is never
           updated with a status lower in ranking
           The current ranking is given by:

           RQ (Requested) < AS (Assigned) < TS (To be submitted) < SB (Submitted) < DN (Done)

        3) Errors are currently not recoverable, i.e., if an audit event reaches
           an error state in the finite automata internally captured by the audit node,
           the event never leaves that state

        4) At all times, there is at most one writer thread executing. Stated otherwise,
           concurrent writes never occur

        5) At all times, the audit node only accounts for the health of threads
           processing new events. Old ones necessarily cause the underlying
           thread to complete execution and eventually dying
"""


class QSPAuditNode(QSPThread):

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        QSPThread.__init__(self, config)

        self.__internal_thread_handles = []
        self.__internal_thread_definitions = []
        self.__is_initialized = False

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

    @staticmethod
    def has_enough_stake(config):
        """
        Returns true if the node has enough stake and false otherwise.
        """
        has_stake = False
        try:
            has_stake = mk_read_only_call(
                config,
                config.audit_contract.functions.hasEnoughStake(config.account))
        except Exception as err:
            config.logger.debug("Failed to check if node has enough stake: {0}".format(err))

        return has_stake

    @staticmethod
    def get_stake_required(config):
        """
        Returns the minimum required stake.
        """
        stake_required = 0
        try:
            stake_required = mk_read_only_call(
                config,
                config.audit_contract.functions.getMinAuditStake())
        except Exception as err:
            config.logger.debug("Failed to check the minimum required stake: {0}".format(err))

        return stake_required

    @staticmethod
    def get_current_stake(config):
        """
        Returns the amount of stake needed.
        """
        staked = 0
        try:
            staked = mk_read_only_call(
                config,
                config.audit_contract.functions.totalStakedFor(config.account))
        except Exception as err:
            config.logger.debug("Failed to check the how much stake is missing: {0}".format(err))

        return staked

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
        handle = submission_thread.start()
        self.__internal_thread_handles.append(handle)

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
        if self.config.metric_collection_is_enabled:
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

    def __start_claim_rewards_thread(self):
        """
        Collects any unclaimed audit rewards every 24 hours.
        """
        claim_rewards_thread = ClaimRewardsThread(self.config)
        self.__internal_thread_definitions.append(claim_rewards_thread)
        handle = claim_rewards_thread.start()
        self.__internal_thread_handles.append(handle)

    def __start_monitor_submission_thread(self):
        monitor_thread = MonitorSubmissionThread(self.config)
        self.__internal_thread_definitions.append(monitor_thread)
        handle = monitor_thread.start()
        self.__internal_thread_handles.append(handle)

    def __timeout_stale_requests(self):
        first_valid_block = self.config.web3_client.eth.blockNumber - \
                            self.config.submission_timeout_limit_blocks + \
                            self.config.block_discard_on_restart

        def timeout_event(evt):
            try:
                if first_valid_block >= evt['block_nbr']:
                    evt['status_info'] = "Submission timeout"
                    self.config.event_pool_manager.set_evt_status_to_error(evt)
            except KeyError as error:
                self.logger.exception(
                    "KeyError when handling timeout on restart: {0}".format(str(error))
                )
            except Exception as error:
                self.logger.exception(
                    "Unexpected error when handling timeout on restart: {0}".format(error))

        self.config.event_pool_manager.process_incoming_events(timeout_event)
        self.config.event_pool_manager.process_events_to_be_submitted(timeout_event)

    def run(self):
        """
        Starts all the threads processing different stages of a given event.
        """
        if self.exec:
            raise Exception(
                "Cannot run audit node thread due to another audit node thread instance")

        if not QSPAuditNode.has_enough_stake(self.config):
            # todo(mderka): The conversion from QSPWei to QSP is hardcoded in order to save a call.
            # todo(mderka): If the node is used with tokens other than QSP, this needs to change.
            minimum = QSPAuditNode.get_stake_required(self.config)
            current_stake = QSPAuditNode.get_current_stake(self.config)
            raise Exception(
                "Audit node does {0} not have enough stake. Please stake at least {1} QSP into "
                "the account {2}. Current stake is {3} QSP. Please restart the node.".format(
                    self.config.account,
                    minimum / (10 ** 18),
                    self.config.audit_contract_address,
                    current_stake / (10 ** 18)))

        # Sets exec to True
        self.start()

        # Upon restart, before processing, set all events that timed out to err
        self.__timeout_stale_requests()

        # Start all the threads
        self.__start_gas_price_thread()  # Analyze and set gas price
        self.__start_min_price_thread()  # Update min price periodically
        self.__start_claim_rewards_thread()  # Collect any unclaimed rewards every 24 hours
        self.__start_metric_collection_thread()  # Submit metrics if enables
        self.__start_poll_requests_thread()  # Poll for audit and police requests
        self.__start_perform_audit_thread()  # Performs audits
        self.__start_submission_thread()  # Submits results
        self.__start_monitor_submission_thread()  # Monitors submission events

        self.__is_initialized = True

        # Monitors the state of each thread in a busy loop fashion. Upon error, terminate the
        # audit node. Checking whether a thread is alive or not does not account for timing out
        # audits, which necessarily dies after processing them all.
        health_check_interval_sec = 2
        self.run_with_interval(self.check_all_threads, health_check_interval_sec)

    def check_all_threads(self):
        if not self.exec:
            return

        thread_lost = None
        # Checking if all threads are still alive
        for thread in self.__internal_thread_handles:
            if not thread.is_alive():
                thread_lost = thread
                break
        if thread_lost is not None:
            raise Exception(
                "Cannot proceed execution. At least one internal thread is not alive ({0})".format(
                    str(thread_lost))
            )

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        QSPThread.stop(self)
        self.logger.info("Stopping QSP Audit Node")

        # indicate to every thread that it should stop its execution
        for internal_thread in self.__internal_thread_definitions:
            self.logger.debug("Thread {0} is signaled to stop.".format(internal_thread.thread_name))
            internal_thread.stop()

        # join every thread
        for internal_thread in self.__internal_thread_handles:
            internal_thread.join()
            self.logger.debug("Thread {0} is stopped.".format(internal_thread.name))

        self.__internal_thread_handles = []
        self.__internal_thread_definitions = []

        # Close resources
        self.config.event_pool_manager.close()

    @property
    def is_initialized(self):
        return self.__is_initialized
