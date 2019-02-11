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
import calendar
import copy
import json
import os

import threading
import time
import traceback
import urllib.parse
import jsonschema

from time import sleep
from web3.utils.threads import Timeout

from utils.eth.tx import TransactionNotConfirmedException
from .exceptions import NotEnoughStake
from evt import is_audit
from evt import is_police_check
from evt import set_evt_as_audit
from evt import set_evt_as_police_check
from log_streaming import get_logger
from utils.io import (
    fetch_file,
    digest,
    digest_file,
    read_file
)
from utils.eth import send_signed_transaction
from utils.eth import mk_read_only_call
from utils.eth import DeduplicationException
from utils.eth import get_gas_price
from .vulnerabilities_set import VulnerabilitiesSet

from threading import Thread
from utils.metrics import MetricCollector
from solc import compile_standard
from solc.exceptions import ContractsNotFound, SolcError
from subprocess import TimeoutExpired


class QSPAuditNode:
    __EVT_AUDIT_ASSIGNED = "LogAuditAssigned"
    __EVT_REPORT_SUBMITTED = "LogAuditFinished"

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAuditData.sol#L14
    __AUDIT_STATE_SUCCESS = 4

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAuditData.sol#L15
    __AUDIT_STATE_ERROR = 5

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAudit.sol#L106
    __AVAILABLE_AUDIT_STATE_READY = 1

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAudit.sol#L110
    __AVAILABLE_AUDIT_UNDERSTAKED = 5

    __AUDIT_STATUS_ERROR = "error"
    __AUDIT_STATUS_SUCCESS = "success"

    # Determines how long threads will sleep between waking up to react to events
    __THREAD_SLEEP_TIME = 0.1

    # The frequency of updating min price. This is not configurable as dashboard logic depends
    # on this frequency
    __MIN_PRICE_BEAT_SEC = 24 * 60 * 60

    # The frequency of checking for claims. Currently, not configurable
    __CLAIM_REWARDS_BEAT_SEC = 24 * 60 * 60

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
        self.__metric_collector = None
        self.__exec = False
        self.__internal_threads = []
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
        last_called = 0
        if not start_with_call:
            last_called = time.time()
        while self.__exec:
            now = time.time()
            if now - last_called > polling_interval:
                body_function()
                last_called = now
            sleep(QSPAuditNode.__THREAD_SLEEP_TIME)

    def __run_block_mined_thread(self, handler_name, handler):
        """
        Checks if a new block is mined. Reacting to a new block the handler is called.
        """
        def exec():
            current_block = 0
            last_called = 0
            while self.__exec:
                now = time.time()
                if now - last_called > self.__config.block_mined_polling:
                    last_called = now
                    if current_block < self.__config.web3_client.eth.blockNumber:
                        current_block = self.__config.web3_client.eth.blockNumber
                        self.__logger.debug("A new block is mined # {0}".format(str(current_block)))
                        try:
                            handler()
                        except Exception as e:
                            self.__logger.exception(
                                "Error in block mined thread handler: {0}".format(str(e)))
                            raise e
                sleep(QSPAuditNode.__THREAD_SLEEP_TIME)

        new_block_monitor_thread = Thread(target=exec, name="{0} thread".format(handler_name))
        new_block_monitor_thread.start()

        return new_block_monitor_thread

    @property
    def config(self):
        return self.__config

    def __compute_gas_price(self):
        """
        Queries recent blocks to set a baseline gas price, or uses a default static gas price
        """
        gas_price = None
        # if we're not using the dynamic gas price strategy, just return the default
        if self.__config.gas_price_strategy == "static":
            gas_price = self.__config.default_gas_price_wei
        else:
            gas_price = get_gas_price(self.__config)
        gas_price = int(min(gas_price, self.__config.max_gas_price_wei))
        # set the gas_price in config
        self.__config.gas_price_wei = gas_price
        self.__logger.debug("Current gas price: {0}".format(str(gas_price)))

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

    def __has_available_rewards(self):
        """
        Checks if any unclaimed rewards are available for the node.
        """
        available_rewards = False
        try:
            available_rewards = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.hasAvailableRewards())
        except Exception as err:
            raise err

        return available_rewards

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

    def run(self):
        """
        Starts all the threads processing different stages of a given event.
        """
        if self.__exec:
            raise Exception("Cannot run audit node thread due to another audit node thread instance")

        self.__exec = True

        # Initialize the gas price
        self.__compute_gas_price()

        if self.config.heartbeat_allowed:
            # Updates min price and starts a thread that will be doing so every 24 hours
            self.__update_min_price()
            min_price_thread = self.__run_update_min_price_thread()
            self.__internal_threads.append(min_price_thread)

        else:
            # Updates min price only if it differs
            self.__check_and_update_min_price()

        # Collect any unclaimed rewards every 24 hours
        claim_rewards_thread = self.__run_claim_rewards_thread()
        self.__internal_threads.append(claim_rewards_thread)

        if self.__config.metric_collection_is_enabled:
            self.__metric_collector = MetricCollector(self.__config)
            self.__metric_collector.collect_and_send()
            self.__internal_threads.append(self.__run_metrics_thread())

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

        self.__internal_threads.append(self.__run_block_mined_thread(
            "poll_requests",
            self.__poll_requests
        ))

        self.__internal_threads.append(self.__run_block_mined_thread(
            "compute_gas_price",
            self.__compute_gas_price
        ))

        # Starts two additional threads for performing audits
        # and eventually submitting results
        self.__internal_threads.append(self.__run_perform_audit_thread())
        self.__internal_threads.append(self.__run_submission_thread())
        self.__internal_threads.append(self.__run_monitor_submisson_thread())

        # Monitors the state of each thread. Upon error, terminate the
        # audit node. Checking whether a thread is alive or not does
        # not account for pastEvent threads, which necessarily die
        # after processing them all

        health_check_interval_sec = 2

        def check_all_threads():
            thread_lost = False
            # Checking if all threads are still alive
            for thread in self.__internal_threads:
                if not thread.is_alive():
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

    def __check_and_update_min_price(self):
        """
        Checks that the minimum price in the audit node's configuration matches the smart contract
        and updates it if it differs.
        """
        contract_price = mk_read_only_call(
            self.__config,
            self.__config.audit_contract.functions.getMinAuditPrice(self.__config.account)
        )
        min_price_in_mini_qsp = self.__config.min_price_in_qsp * (10 ** 18)
        if min_price_in_mini_qsp != contract_price:
            self.__update_min_price()

    def __run_update_min_price_thread(self):
        """
        Updates min price every 24 hours.
        """
        def exec():
            self.__run_with_interval(self.__update_min_price, QSPAuditNode.__MIN_PRICE_BEAT_SEC,
                                     start_with_call=False)

        min_price_thread = Thread(target=exec, name="update min price thread")
        min_price_thread.start()

        return min_price_thread

    def __update_min_price(self):
        """
        Updates smart contract with the minimum price in the audit node's configuration.
        """
        msg = "Make sure the account has enough Ether, " \
              + "the Ethereum node is connected and synced, " \
              + "and restart your node to try again."

        min_price_in_mini_qsp = self.__config.min_price_in_qsp * (10 ** 18)
        self.__logger.info(
            "Updating min_price in the smart contract for address {0}.".format(
                self.__config.account
            ))
        transaction = self.__config.audit_contract.functions.setAuditNodePrice(
            min_price_in_mini_qsp)
        try:
            tx_hash = send_signed_transaction(self.__config,
                                              transaction,
                                              wait_for_transaction_receipt=True)
            # If the tx_hash is None, the transaction did not actually complete. Exit
            if not tx_hash:
                raise Exception("The min price transaction did not complete")
            self.__logger.debug("Successfully updated min price to {0}.".format(
                self.__config.min_price_in_qsp))
        except Timeout as e:
            error_msg = "Update min price timed out. " + msg + " {0}, {1}."
            self.__logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except DeduplicationException as e:
            error_msg = "A transaction already exists for updating min price," \
                        + " but has not yet been mined. " + msg \
                        + " This may take several iterations. {0}, {1}."
            self.__logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except TransactionNotConfirmedException as e:
            error_msg = "A transaction occurred, but was then uncled and never recovered. {0}, {1}"
            self.__logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except Exception as e:
            error_msg = "Error occurred setting min price. " + msg + " {0}, {1}."
            self.__logger.exception(error_msg.format(
                str(transaction),
                str(e)))
            raise e

    def __run_claim_rewards_thread(self):
        """
        Collects any unclaimed audit rewards every 24 hours.
        """
        def exec():
            self.__run_with_interval(self.__claim_rewards_if_available, QSPAuditNode.__CLAIM_REWARDS_BEAT_SEC,
                                     start_with_call=True)

        claim_rewards_thread = Thread(target=exec, name="claim rewards thread")
        claim_rewards_thread.start()

        return claim_rewards_thread

    def __claim_rewards_if_available(self):
        """
        Claims any unclaimed rewards, if available.
        """
        self.__logger.info(
            "Checking for any available rewards for address {0}.".format(
                self.__config.account
            ))

        available_rewards = self.__has_available_rewards()
        if not available_rewards:
            self.__logger.info(
                "There are no available rewards for address {0}.".format(
                    self.__config.account
                ))
        else:
            try:
                self.__claim_rewards()
            except Exception as error:
                self.__logger.warning("Could not claim rewards: {0}".format(error))

    def __claim_rewards(self):
        """
        Invokes the claimRewards function in the smart contract.
        """
        msg = "Make sure the account has enough Ether, " \
            + "the Ethereum node is connected and synced, " \
            + "and restart your node to try again."

        transaction = self.__config.audit_contract.functions.claimRewards()
        tx_hash = None
        try:
            tx_hash = send_signed_transaction(self.__config,
                                              transaction,
                                              wait_for_transaction_receipt=True)
            # If the tx_hash is None, the transaction did not actually complete. Exit
            if not tx_hash:
                raise Exception("The claim rewards transaction did not complete")
            self.__logger.debug("Successfully claimed rewards for address {0}.".format(
                self.__config.account))
        except Timeout as e:
            error_msg = "Claim rewards timed out. " + msg + " {0}, {1}."
            self.__logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except DeduplicationException as e:
            error_msg = "A transaction already exists for claiming rewards," \
                        + " but has not yet been mined. " + msg \
                        + " This may take several iterations. {0}, {1}."
            self.__logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except TransactionNotConfirmedException as e:
            error_msg = "A transaction occurred, but was then uncled and never recovered. {0}, {1}"
            self.__logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except Exception as e:
            error_msg = "Error occurred claiming rewards. " + msg + " {0}, {1}."
            self.__logger.exception(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        return tx_hash

    def __add_evt_to_db(self, request_id, requestor, uri, price, block_nbr, is_audit=True):
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

    def __run_perform_audit_thread(self):
        def process_audit_request(evt):
            request_id = None
            try:
                requestor = evt['requestor']
                request_id = evt['request_id']
                contract_uri = evt['contract_uri']

                report_type = "police" if is_police_check(evt) else "audit"
                audit_result = self.audit(requestor, contract_uri, request_id, report_type)

                if audit_result is None:
                    error = "Could not generate {0} report".format(report_type)
                    evt['status_info'] = error
                    evt['compressed_report'] = QSPAuditNode.__EMPTY_COMPRESSED_REPORT
                    self.__logger.exception(error, requestId=request_id)
                    self.__config.event_pool_manager.set_evt_to_error(evt)
                else:
                    evt['audit_uri'] = audit_result['audit_uri']
                    evt['audit_hash'] = audit_result['audit_hash']
                    evt['audit_state'] = audit_result['audit_state']
                    evt['full_report'] = audit_result['full_report']
                    evt['compressed_report'] = audit_result['compressed_report']
                    evt['status_info'] = "Successfully generated report"
                    msg = "Generated report URI is {0}. Saving it in the internal database " \
                          "(if not previously saved)"
                    self.__logger.debug(
                        msg.format(str(evt['audit_uri'])), requestId=request_id, evt=evt
                    )
                    self.__config.event_pool_manager.set_evt_status_to_be_submitted(evt)
            except KeyError as error:
                self.__logger.exception(
                    "KeyError when trying to produce {0} report from request event {1}: {2}".format(report_type, evt, error),
                    requestId=request_id
                )
            except Exception as error:
                self.__logger.exception(
                    "Error when trying to produce {0} report from request event {1}: {2}".format(report_type, evt, error),
                    requestId=request_id,
                )
                evt['status_info'] = traceback.format_exc()
                self.__config.event_pool_manager.set_evt_status_to_error(evt)

        def process_incoming():
            self.__config.event_pool_manager.process_incoming_events(
                process_audit_request
            )

        def exec():
            self.__run_with_interval(process_incoming, self.__config.evt_polling)

        audit_thread = Thread(target=exec, name="audit thread")
        self.__internal_threads.append(audit_thread)
        audit_thread.start()

        return audit_thread

    def __get_next_police_assignment(self):
        """
        Gets the next police assignment tuple.
        """
        return mk_read_only_call(
            self.__config,
            self.__config.audit_contract.functions.getNextPoliceAssignment()
        )

    def __get_report_in_blockchain(self, request_id):
        """
        Gets a compressed report already stored in the blockchain.
        """
        compressed_report_bytes = mk_read_only_call(
            self.__config,
            self.__config.audit_contract.functions.getReport(request_id)
        )
        if compressed_report_bytes is None or len(compressed_report_bytes) == 0:
            return None

        return compressed_report_bytes.hex()

    def __is_report_deemed_correct(self, request_id, full_police_report):
        """
        Checks whether an audit report should be deemed correct using
        a police (full) report as a baseline for comparison. Reports are deemed
        correct if they have at least __SIMILARITY_THRESHOLD (%) of the
        vulnerabilities reported by the police.
        """
        compressed_audit_report = self.__get_report_in_blockchain(
            request_id
        )

        # If the compressed audit report cannot be found, just raise an exception.
        if compressed_audit_report is None:
            raise Exception(
                "Report for request_id {0} not found".format(request_id)
            )

        # Decompress the audit report
        try:
            decompressed_audit_report = self.__config.report_encoder.decode_report(
                compressed_audit_report,
                request_id
            )
            self.__validate_json(decompressed_audit_report, request_id)
        except Exception as err:
            self.__logger.debug("Cannot decompress the audit report: {0}".format(err))
            return False

        # Makes sure the contract_hashes in both the compressed report and the police match
        audit_contract_hash = decompressed_audit_report.get('contract_hash', "").lower()
        police_contract_hash = full_police_report.get('contract_hash', "").lower()
        if not audit_contract_hash or not police_contract_hash or audit_contract_hash != police_contract_hash:
            self.__logger.debug(
                "Police check: reports for request ID {0} have different contract hashes: {1} {2}"
                    .format(str(request_id),
                            str(decompressed_audit_report.get('contract_hash', None)),
                            str(full_police_report.get('contract_hash', None))))
            return False

        # If report exists, but building a vulnerability set fails,
        # deem the report as incorrect
        try:
            auditor_vulnerabilities = VulnerabilitiesSet.from_uncompressed_report(
                decompressed_audit_report
            )
        except Exception as err:
            self.__logger.debug("Cannot build vulnerability set: {0}".format(err))
            return False

        police_vulnerabilities = VulnerabilitiesSet.from_uncompressed_report(full_police_report)

        # Accounts for the case where the police cannot find any
        # vulnerability
        if len(police_vulnerabilities) == 0:
            return True

        similarity = len(auditor_vulnerabilities & police_vulnerabilities) / len(police_vulnerabilities)
        return similarity >= QSPAuditNode.__SIMILARITY_THRESHOLD

    def __run_submission_thread(self):
        def process_submission_request(evt):
            try:
                tx_hash = None
                request_id = int(evt['request_id'])
                # If the audit is not a police check,
                # submit it as a conventional audit
                if is_audit(evt):
                    tx_hash = self.__submit_audit_report(
                        request_id,
                        evt['audit_state'],
                        evt['compressed_report'],
                    )
                # If the audit is a police check,
                # submit it as such
                elif is_police_check(evt):
                    police_report = json.loads(evt['full_report'])
                    police_check_result = self.__is_report_deemed_correct(
                        request_id,
                        police_report
                    )
                    self.__logger.debug("Police check: report {} correct".format("is" if police_check_result else "is not"))

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
                self.__config.event_pool_manager.set_evt_status_to_submitted(evt)
                self.__on_successful_submission(int(evt['request_id']))
            except DeduplicationException as error:
                self.__logger.debug(
                    "Error when submiting report {0}".format(str(error))
                )
            except TransactionNotConfirmedException as error:
                error_msg = "A transaction occurred, but was then uncled and never recovered. {0}"
                self.__logger.debug(error_msg.format(str(error)))
            except KeyError as error:
                self.__logger.exception(
                    "KeyError when processing submission event: {0}".format(str(error))
                )
            except Exception as error:
                self.__logger.exception(
                    "Error when processing submission event {0}: {1}.".format(
                        str(evt['request_id']),
                        str(error),
                    ),
                    requestId=evt['request_id'],
                )
                evt['status_info'] = traceback.format_exc()
                self.__config.event_pool_manager.set_evt_status_to_error(evt)

        def process_to_be_submitted():
            self.__config.event_pool_manager.process_events_to_be_submitted(
                process_submission_request
            )

        def exec():
            self.__run_with_interval(process_to_be_submitted, self.__config.evt_polling)

        submission_thread = Thread(target=exec, name="submission thread")
        self.__internal_threads.append(submission_thread)
        submission_thread.start()

        return submission_thread

    def __on_successful_submission(self, request_id):
        audit_evt = None
        try:
            is_finished = mk_read_only_call(
                self.config, self.__config.audit_contract.functions.isAuditFinished(request_id)
            )
            audit_evt = self.__config.event_pool_manager.get_event_by_request_id(request_id)
            if is_finished and audit_evt != {}:
                audit_evt['status_info'] = 'Report successfully submitted'
                self.__config.event_pool_manager.set_evt_status_to_done(audit_evt)
                self.__logger.debug(
                    "Report successfully submitted for event: {0}".format(
                        str(audit_evt)
                    ),
                    request_id=request_id
                )

        except KeyError as error:
            self.__logger.exception(
                "KeyError when processing submission event: {0}".format(str(error))
            )
        except Exception as error:
            self.__logger.exception(
                "Error when processing changing event status: {0}. Audit event is {1}".format(
                    str(error),
                    str(audit_evt)
                ),
                requestId=request_id
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
        self.__internal_threads.append(monitor_thread)
        monitor_thread.start()

        return monitor_thread

    def __run_metrics_thread(self):
        def exec():
            self.__run_with_interval(self.__metric_collector.collect_and_send,
                                     self.__config.metric_collection_interval_seconds)

        metrics_thread = Thread(target=exec, name="metrics thread")
        self.__internal_threads.append(metrics_thread)
        metrics_thread.start()

        return metrics_thread

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """

        self.__logger.info("Stopping QSP Audit Node")
        self.__exec = False

        for internal_thread in self.__internal_threads:
            internal_thread.join()
            self.__logger.debug("Thread {0} is stopped.".format(internal_thread.name))

        self.__internal_threads = []

        # Close resources
        self.__config.event_pool_manager.close()

    def __validate_json(self, report, request_id):
        """
        Validate that the report conforms to the schema.
        """
        try:
            file_path = os.path.realpath(__file__)
            schema_file = '{0}/../../../plugins/analyzers/schema/analyzer_integration.json'.format(
                os.path.dirname(file_path))
            with open(schema_file) as schema_data:
                schema = json.load(schema_data)
            jsonschema.validate(report, schema)
            return report
        except jsonschema.ValidationError as e:
            self.__logger.exception(
                "Error: JSON could not be validated: {0}.".format(str(e)),
                requestId=request_id,
            )
            raise Exception("JSON could not be validated") from e

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

        self.__logger.info(
            "Analyzer report contents",
            requestId=request_id,
            contents=audit_report,
        )
        return target_contract, audit_report

    def audit(self, requestor, uri, request_id, report_type):
        """
        Audits a target contract.
        """
        self.__logger.info(
            "Executing {0} check on contract at {1}".format(report_type, uri),
            requestId=request_id,
        )
        target_contract, audit_report = self.get_full_report(requestor, uri, request_id)

        self.__validate_json(audit_report, request_id)

        compressed_report = self.__config.report_encoder.compress_report(audit_report,
                                                                         request_id)

        audit_report_str = json.dumps(audit_report, indent=2)
        audit_hash = digest(audit_report_str)

        upload_result = self.__config.upload_provider.upload_report(audit_report_str,
                                                                    audit_report_hash=audit_hash)

        self.__logger.info(
            "Report upload result: {0}".format(upload_result),
            requestId=request_id,
        )

        if not upload_result['success']:
            raise Exception("Error uploading {0} report: {1}".format(report_type, json.dumps(upload_result)))

        parse_uri = urllib.parse.urlparse(uri)
        original_file_name = os.path.basename(parse_uri.path)
        contract_body = read_file(target_contract)
        contract_upload_result = self.__config.upload_provider.upload_contract(request_id,
                                                                               contract_body,
                                                                               original_file_name)
        if contract_upload_result['success']:
            self.__logger.info(
                "Contract upload result: {0}".format(contract_upload_result),
                requestId=request_id,
            )
        else:
            # We just log on error, not raise an exception
            self.__logger.error(
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

    def get_audit_report_from_analyzers(self, target_contract, requestor, uri, request_id):
        number_of_analyzers = len(self.__config.analyzers)

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
                report = self.__config.analyzers[analyzer_id].check(
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
        for i, analyzer in enumerate(self.__config.analyzers):
            shared_reports.append({})
            local_reports.append({})
            report_locks.append(threading.RLock())
            wrappers.append(self.__config.analyzers[i].wrapper)
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
                local_reports[i]['status'] = 'error'

            # A timeout has not occurred. Register the end time
            end_time = calendar.timegm(time.gmtime())
            local_reports[i]['end_time'] = end_time

        audit_report = {
            'timestamp': calendar.timegm(time.gmtime()),
            'contract_uri': uri,
            'contract_hash': digest_file(target_contract),
            'requestor': requestor,
            'auditor': self.__config.account,
            'request_id': request_id,
            'version': self.__config.node_version,
        }

        # FIXME
        # This is currently a very simple mechanism to claim an audit as
        # successful or not. Either it is fully successful (all analyzers
        # produce a successful result), or fails otherwise.
        audit_state = QSPAuditNode.__AUDIT_STATE_SUCCESS
        audit_status = QSPAuditNode.__AUDIT_STATUS_SUCCESS

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
                audit_state = QSPAuditNode.__AUDIT_STATE_ERROR
                audit_status = QSPAuditNode.__AUDIT_STATUS_ERROR

        audit_report['audit_state'] = audit_state
        audit_report['status'] = audit_status

        if len(local_reports) > 0:
            audit_report['analyzers_reports'] = local_reports

        return audit_report

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

    def __submit_audit_report(self, request_id, audit_state, compressed_report):
        """
        Submits the audit report to the entire QSP network.
        """
        # Convert from a bitstring to a bytes array
        compressed_report_bytes = self.__config.web3_client.toBytes(hexstr=compressed_report)

        tx_hash = send_signed_transaction(self.__config,
                                          self.__config.audit_contract.functions.submitReport(
                                            request_id,
                                            audit_state,
                                            compressed_report_bytes))
        self.__logger.debug("Audit report submitted", requestId=request_id)
        return tx_hash

    def __submit_police_report(self, request_id, compressed_report, is_verified):
        """
        Submits the police report to the entire QSP network.
        """
        # Convert from a bitstring to a bytes array
        compressed_report_bytes = self.__config.web3_client.toBytes(hexstr=compressed_report)

        tx_hash = send_signed_transaction(self.__config,
                                          self.__config.audit_contract.functions.submitPoliceReport(
                                            request_id,
                                            compressed_report_bytes,
                                            is_verified))
        self.__logger.debug("Police report submitted", requestId=request_id)
        return tx_hash

    def __create_err_result(self, errors, warnings, request_id, requestor, uri, target_contract):
        result = {
            'timestamp': calendar.timegm(time.gmtime()),
            'contract_uri': uri,
            'contract_hash': digest_file(target_contract),
            'requestor': requestor,
            'auditor': self.__config.account,
            'request_id': request_id,
            'version': self.__config.node_version,
            'audit_state': QSPAuditNode.__AUDIT_STATE_ERROR,
            'status': QSPAuditNode.__AUDIT_STATUS_ERROR,
        }
        if errors is not None and len(errors) != 0:
            result['compilation_errors'] = errors
        if warnings is not None and len(warnings) != 0:
            result['compilation_warnings'] = warnings

        return result

    def check_compilation(self, contract, request_id, uri):
        self.__logger.debug("Running compilation check. About to check {0}".format(contract),
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
            self.__logger.debug(
                "ContractsNotFound before calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            errors += [str(error)]
        except SolcError as error:
            self.__logger.debug(
                "SolcError before calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            errors += [str(error)]
        except KeyError as error:
            self.__logger.error(
                "KeyError when calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            # This is thrown because a bug in our own code. We only log, but do not record the error
            # so that the analyzers are still executed.
        except Exception as error:
            self.__logger.error(
                "Error before calling analyzers: {0}".format(str(error)),
                requestId=request_id)
            errors += [str(error)]

        return warnings, errors

    @property
    def is_initialized(self):
        return self.__is_initialized
