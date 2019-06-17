####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Provides the QSP Audit node implementation.
"""

from .threads import ClaimRewardsThread
from .threads import CollectMetricsThread
from .threads import ComputeGasPriceThread
from .threads import PollRequestsThread
from .threads import SubmitReportThread
from .threads import PerformAuditThread
from .threads import MonitorSubmissionThread

from log_streaming import get_logger
from utils.eth import mk_read_only_call
from utils.eth import DeduplicationException
from utils.eth import send_signed_transaction
from utils.eth.tx import TransactionNotConfirmedException
from web3.utils.threads import Timeout

from time import sleep

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


class QSPAuditNode:

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__exec = False
        self.__config = config
        self.__is_initialized = False
        self.__logger = get_logger(self.__class__.__qualname__)

        self.__internal_threads = [
            ComputeGasPriceThread(config),
            ClaimRewardsThread(config),
            PollRequestsThread(config),
            PerformAuditThread(config),
            SubmitReportThread(config),
            MonitorSubmissionThread(config)
        ]

        if config.metric_collection_is_enabled:
            self.__internal_threads.append(CollectMetricsThread(config))

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

    def __timeout_stale_requests(self):
        first_valid_block = self.config.web3_client.eth.blockNumber - \
                            self.config.submission_timeout_limit_blocks + \
                            self.config.block_discard_on_restart

        def timeout_event(evt):
            try:
                if first_valid_block >= evt['assigned_block_nbr']:
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

    def __check_stake(self):
        if QSPAuditNode.is_police_officer(self.config) \
                and not self.config.enable_police_audit_polling:
            return

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

    def __update_min_price(self):
        """
        Updates smart contract with the minimum price in the audit node's configuration.
        """
        msg = "Make sure the account has enough Ether, " \
              + "the Ethereum node is connected and synced, " \
              + "and restart your node to try again."

        min_price_in_mini_qsp = self.config.min_price_in_qsp * (10 ** 18)
        self.logger.info(
            "Updating min_price in the smart contract for address {0}.".format(
                self.config.account
            ))
        transaction = self.config.audit_contract.functions.setAuditNodePrice(
            min_price_in_mini_qsp)
        try:
            tx_hash = send_signed_transaction(self.config,
                                              transaction,
                                              wait_for_transaction_receipt=True)
            # If the tx_hash is None, the transaction did not actually complete. Exit
            if not tx_hash:
                raise Exception("The min price transaction did not complete")
            self.logger.debug("Successfully updated min price to {0}.".format(
                self.config.min_price_in_qsp))
        except Timeout as e:
            error_msg = "Update min price timed out, " \
                + "increase the tx_timeout_seconds in config.yaml and restart the node. " \
                + msg + " {0}, {1}."
            formatted_error = error_msg.format(
                str(transaction),
                str(e))
            self.logger.debug(formatted_error)
            raise Timeout(formatted_error) from e
        except DeduplicationException as e:
            error_msg = "A transaction already exists for updating min price," \
                        + " but has not yet been mined. " + msg \
                        + " This may take several iterations. {0}, {1}."
            self.logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except TransactionNotConfirmedException as e:
            error_msg = "A transaction occurred, but was then uncled and never recovered. {0}, {1}"
            self.logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except Exception as e:
            error_msg = "Error occurred setting min price. " + msg + " {0}, {1}."
            self.logger.exception(error_msg.format(
                str(transaction),
                str(e)))
            raise e

    def __check_and_update_min_price(self):
        """
        Checks that the minimum price in the audit node's configuration matches the smart contract
        and updates it if it differs. This is a blocking function.
        """
        contract_price = mk_read_only_call(
            self.config,
            self.config.audit_contract.functions.getMinAuditPrice(self.config.account)
        )
        min_price_in_mini_qsp = self.config.min_price_in_qsp * (10 ** 18)
        if min_price_in_mini_qsp != contract_price:
            self.__update_min_price()

    def start(self):
        """
        Starts all the threads processing different stages of a given event.
        Can only be called once.
        """
        if self.__exec:
            raise Exception(
                "Cannot run audit node thread due to another audit node thread instance")

        self.__exec = True
        self.__check_stake()
        self.__check_and_update_min_price()

        # Upon restart, before processing, set all events that timed out to err
        self.__timeout_stale_requests()

        # Start all the threads
        for thread in self.__internal_threads:
            thread.start()

        self.__is_initialized = True

        # Monitors the state of each thread in a busy loop fashion. Upon error, terminate the
        # audit node. Checking whether a thread is alive or not does not account for timing out
        # audits, which necessarily dies after processing them all.
        health_check_interval_sec = 2

        while self.__exec:
            self.__check_all_threads()
            sleep(health_check_interval_sec)

    def __check_all_threads(self):
        if not self.__exec:
            return

        thread_lost = None
        # Checking if all threads are still alive
        for thread in self.__internal_threads:
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
        self.__exec = False
        self.logger.info("Stopping QSP Audit Node")

        skip = []
        # indicate to every thread that it should stop its execution
        for thread in self.__internal_threads:
            if thread.exec:
                self.logger.debug("Thread {0} is signaled to stop.".format(thread.name))
                thread.stop()
            else:
                skip += [thread]
                self.logger.debug("Thread {0} was never started.".format(thread.name))

        # join every thread
        for thread in self.__internal_threads:
            if thread not in skip:
                thread.join()
                self.logger.debug("Thread {0} is joined and stopped.".format(thread.name))
            else:
                self.logger.debug("Thread {0} does not need to be joined.".format(thread.name))

        self.__is_initialized = False

        # Close resources
        self.config.event_pool_manager.close()

    @property
    def exec(self):
        return self.__exec

    @property
    def is_initialized(self):
        return self.__is_initialized

    @property
    def config(self):
        return self.__config

    @property
    def logger(self):
        return self.__logger
