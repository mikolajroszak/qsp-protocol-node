####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread that claims rewards in the QSP Audit node implementation.
"""

from threading import Thread
from utils.eth import DeduplicationException
from utils.eth import mk_read_only_call
from utils.eth import send_signed_transaction
from utils.eth.tx import TransactionNotConfirmedException
from web3.utils.threads import Timeout

from .qsp_thread import QSPThread


class ClaimRewardsThread(QSPThread):
    # The frequency of checking for claims. Currently, not configurable
    __CLAIM_REWARDS_BEAT_SEC = 24 * 60 * 60

    def __init__(self, config):
        """
        Builds the thread object from the given input parameters.
        """
        QSPThread.__init__(self, config)

    def start(self):
        """
        Starts the process that claims rewards when available.
        """
        rewards_thread = Thread(target=self.__execute, name="claim rewards thread")
        rewards_thread.start()
        return rewards_thread

    def __execute(self):
        """
        Defines the function to be executed and how often.
        """
        self.run_with_interval(self.__claim_rewards_if_available,
                               ClaimRewardsThread.__CLAIM_REWARDS_BEAT_SEC,
                               start_with_call=True)

    def __claim_rewards_if_available(self):
        """
        Claims any unclaimed rewards, if available.
        """
        self.logger.info(
            "Checking for any available rewards for address {0}.".format(
                self.config.account
            ))

        available_rewards = self.__has_available_rewards()
        if available_rewards:
            try:
                self.__claim_rewards()
            except Exception as error:
                self.logger.warning("Could not claim rewards: {0}".format(error))
        else:
            self.logger.info(
                "There are no available rewards for address {0}.".format(
                    self.config.account
                ))

    def __claim_rewards(self):
        """
        Invokes the claimRewards function in the smart contract.
        """
        msg = "Make sure the account has enough Ether, " \
              + "the Ethereum node is connected and synced, " \
              + "and restart your node to try again."

        transaction = self.config.audit_contract.functions.claimRewards()
        tx_hash = None
        try:
            tx_hash = send_signed_transaction(self.config,
                                              transaction,
                                              wait_for_transaction_receipt=True)
            # If the tx_hash is None, the transaction did not actually complete. Exit
            if not tx_hash:
                raise Exception("The claim rewards transaction did not complete")
            self.logger.debug("Successfully claimed rewards for address {0}.".format(
                self.config.account))
        except Timeout as e:
            error_msg = "Claim rewards timed out. " + msg + " {0}, {1}."
            self.logger.debug(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        except DeduplicationException as e:
            error_msg = "A transaction already exists for claiming rewards," \
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
            error_msg = "Error occurred claiming rewards. " + msg + " {0}, {1}."
            self.logger.exception(error_msg.format(
                str(transaction),
                str(e)))
            raise e
        return tx_hash

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
