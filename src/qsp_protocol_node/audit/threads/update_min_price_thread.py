####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread updating the min price for the QSP Audit node implementation.
"""

from .qsp_thread import TimeIntervalPollingThread
from utils.eth import DeduplicationException
from utils.eth import mk_read_only_call
from utils.eth import send_signed_transaction
from utils.eth.tx import TransactionNotConfirmedException
from web3.utils.threads import Timeout


class UpdateMinPriceThread(TimeIntervalPollingThread):

    def update_min_price(self):
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

    def check_and_update_min_price(self):
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
            self.update_min_price()

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        # The frequency of updating the min proce is not configurable as
        # the dashboard logic depends on this frequency
        TimeIntervalPollingThread.__init__(
            self,
            config=config,
            target_function=self.update_min_price,
            polling_interval=24 * 60 * 60,
            thread_name="update min price thread")

        if self.config.heartbeat_allowed:
            # Updates min price and starts a thread that will be doing so every 24 hours
            self.update_min_price()
        else:
            # Updates min price only if it differs
            self.check_and_update_min_price()
