####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread for polling requests for the QSP Audit node implementation.
"""

from .qsp_thread import BlockMinedPollingThread
from utils.eth import send_signed_transaction
from utils.eth import mk_read_only_call
from utils.eth import DeduplicationException
from utils.eth.tx import TransactionNotConfirmedException
from web3.utils.threads import Timeout
from evt import set_evt_as_audit
from evt import set_evt_as_police_check


class NotEnoughStake(Exception):
    pass


class PollRequestsThread(BlockMinedPollingThread):
    __EVT_AUDIT_ASSIGNED = "LogAuditAssigned"

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAudit.sol#L106
    __AVAILABLE_AUDIT_STATE_READY = 1

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop/contracts/QuantstampAudit.sol#L110
    __AVAILABLE_AUDIT_UNDERSTAKED = 5

    def __on_block_mined(self, *unused):
        self.__poll_requests()

    def __get_min_stake_qsp(self):
        """
        Gets the minimum staking (in QSP) required to perform an audit.
        """
        min_stake = mk_read_only_call(
            self.config,
            self.config.audit_contract.functions.getMinAuditStake())

        # Puts the result (wei-QSP) back to QSP
        return min_stake / (10 ** 18)

    def __add_evt_to_db(self, request_id, requestor, uri, price, assigned_block_nbr, is_audit=True):
        evt = {}
        try:
            evt = {
                'request_id': request_id,
                'requestor': requestor,
                'contract_uri': uri,
                'evt_name': PollRequestsThread.__EVT_AUDIT_ASSIGNED,
                'assigned_block_nbr': assigned_block_nbr,
                'status_info': "Audit Assigned",
                'price': price,
            }
            evt = set_evt_as_audit(evt) if is_audit else set_evt_as_police_check(evt)
            self.config.event_pool_manager.add_evt_to_be_assigned(evt)
        except KeyError as error:
            self.logger.exception(
                "KeyError when processing audit assigned event: {0}".format(str(error))
            )
        except Exception as error:
            self.logger.exception(
                "Error when processing audit assigned event {0}: {1}".format(str(evt), str(error)),
                requestId=request_id,
            )
            self.config.event_pool_manager.set_evt_status_to_error(evt)

    def __get_next_audit_request(self):
        """
        Attempts to get a request from the audit request queue.
        """
        # NOTE
        # The audit contract checks whether the node has enough stake before
        # accepting a bid. No need to replicate that logic here.
        transaction = self.config.audit_contract.functions.getNextAuditRequest()
        tx_hash = None
        try:
            tx_hash = send_signed_transaction(
                self.config,
                transaction,
                wait_for_transaction_receipt=True)
            self.logger.debug("A getNextAuditRequest transaction has been sent in "
                              "transaction {0}".format(tx_hash))
        except Timeout as e:
            self.logger.debug("Transaction receipt timeout happened for {0}. {1}".format(
                str(transaction),
                e))
        return tx_hash

    def __poll_audit_request(self):
        """
        Checks first an audit is assignable; then, bids to get an audit request.
        If successful, save the event in the database to move it along the audit pipeline.
        """
        from audit.audit import QSPAuditNode
        if QSPAuditNode.is_police_officer(self.config) and \
            not self.config.enable_police_audit_polling:
            return

        try:
            most_recent_audit = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.myMostRecentAssignedAudit()
            )

            request_id = most_recent_audit[0]
            audit_assignment_block_number = most_recent_audit[4]
            current_block = self.config.web3_client.eth.blockNumber

            # Check if the most recent audit has been confirmed for N blocks. A consequence of this
            # is that the audit node will not call getNextAuditRequest again while a previous call
            # is not confirmed. If alternative approaches are developed, they should carefully
            # consider possibly adverse interactions between myMostRecentAssignedAudit and
            # waiting for confirmation.
            if audit_assignment_block_number != 0 and \
                audit_assignment_block_number + self.config.n_blocks_confirmation > current_block:
                # Check again when the next block is mined
                return

            # Checks if a previous bid was won. If so, it saves the event to the
            # database for processing by other threads and continues bidding
            # upon an available request

            new_assigned_request = (request_id != 0) and not self.config.event_pool_manager.is_request_processed(
                request_id=request_id
            )

            if new_assigned_request:
                # New request id in (bid won). Persists the event in the database
                self.__add_evt_to_db(
                    request_id=request_id,
                    requestor=most_recent_audit[1],
                    uri=most_recent_audit[2],
                    price=most_recent_audit[3],
                    assigned_block_nbr=audit_assignment_block_number
                )

            # The node should attempt to bid. Before that, though, gotta perform some checks...

            pending_requests_count = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.assignedRequestCount(self.config.account))

            if pending_requests_count >= self.config.max_assigned_requests:
                self.logger.error("Skip bidding as node is currently processing {0} requests in "
                                  "audit contract {1}".format(str(pending_requests_count),
                                                              self.config.audit_contract_address))
                return
            any_request_available = mk_read_only_call(
                self.config,
                self.config.audit_contract.functions.anyRequestAvailable())

            if any_request_available == self.__AVAILABLE_AUDIT_UNDERSTAKED:
                raise NotEnoughStake("Missing funds. To audit contracts, nodes must stake at "
                                     "least {0} QSP".format(self.__get_min_stake_qsp()))

            if any_request_available == self.__AVAILABLE_AUDIT_STATE_READY:
                self.logger.debug("There is request available to bid on in contract {0}.".format(
                    self.config.audit_contract_address))

                # At this point, the node is ready to bid. As such,
                # it tries to get the next audit request
                self.__get_next_audit_request()
            else:
                self.logger.debug("No request available as the contract {0} returned {1}.".format(
                    self.config.audit_contract_address, str(any_request_available)))

        except NotEnoughStake as error:
            self.logger.error("Cannot poll for audit request: {0}".format(str(error)))

        except DeduplicationException as error:
            self.logger.debug(
                "Error when attempting to perform an audit request: {0}".format(str(error))
            )
        except TransactionNotConfirmedException as error:
            error_msg = "A transaction occurred, but was then uncled and never recovered. {0}"
            self.logger.debug(error_msg.format(str(error)))
        except Exception as error:
            self.logger.exception(str(error))

    def __get_next_police_assignment(self):
        """
        Gets the next police assignment tuple.
        """
        return mk_read_only_call(
            self.config,
            self.config.audit_contract.functions.getNextPoliceAssignment()
        )

    def __poll_police_request(self):
        """
        Polls the audit contract for police requests (aka assignments). If the
        node is not a police officer, do nothing. Otherwise, save the event in
        the database to move it along the audit pipeline.
        """
        from audit.audit import QSPAuditNode
        if not QSPAuditNode.is_police_officer(self.config):
            return

        try:
            probe = self.__get_next_police_assignment()
            has_assignment = probe[0]

            police_assignment_block_number = probe[4]
            current_block = self.config.web3_client.eth.blockNumber

            already_processed = self.config.event_pool_manager.is_request_processed(
                request_id=probe[1]
            )

            # If the police node does not have an assignment
            # or has one that has been already processed, do nothing
            if already_processed or not has_assignment:
                return

            # Check if the most recent police assignment has been confirmed for N blocks.
            if police_assignment_block_number + self.config.n_blocks_confirmation > current_block:
                # Check again when the next block is mined
                return

            # Otherwise, save to DB
            self.__add_evt_to_db(
                request_id=probe[1],
                requestor=self.config.audit_contract_address,
                price=probe[2],
                uri=probe[3],
                assigned_block_nbr=police_assignment_block_number,
                is_audit=False)

        except Exception as error:
            self.logger.exception("Error polling police requests: {0}".format(str(error)))

    def __poll_requests(self):
        """
        Polls the audit contract for any possible requests.
        """
        self.__poll_audit_request()
        self.__poll_police_request()

    def __init__(self, config):
        """
        Builds the thread object from the given input parameters.
        """
        BlockMinedPollingThread.__init__(
            self,
            config=config,
            target_function=self.__on_block_mined,
            thread_name="poll_requests thread"
        )
