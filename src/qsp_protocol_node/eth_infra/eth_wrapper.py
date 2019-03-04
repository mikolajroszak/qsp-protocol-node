
####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from component import BaseConfigComponent
from utils.thread import SingletonLock

class EthWrapper(BaseConfigComponent):

    def __init__(self, account, gas_price_calculator, web3_client, block_mined_polling_sec, n_blocks_confirmation):
        super().__init__({
            'account': account,
            'gas_price_calculator': gas_price_calculator,
            'web3_client': web3_client,
            'block_mined_polling_sec': block_mined_polling_sec,
            'n_blocks_confirmation': n_blocks_confirmation
        })

    def mk_args(self):
        gas_limit = self.gas_price_calculator.limit
        gas_price_wei = self.gas_price_calculator.price_wei
        if gas_limit is None:
            args = {'from': self.account.address, 'gasPrice': gas_price_wei}
        else:
            gas_value = int(gas_limit)
            if gas_value >= 0:
                args = {'from': self.__account, 'gas': gas_value, 'gasPrice': gas_price_wei}
            else:
                raise ValueError("The gas value is negative: " + str(gas_value))

        return args


    def mk_read_only_call(self, method):
        try:
            SingletonLock.instance().lock.acquire()
            return method.call({'from': self.account.address})
        finally:
            try:
                SingletonLock.instance().lock.release()
            except Exception as error:
                self.get_logger().debug(
                    "Error when releasing a lock in a read-only call transaction {0}".format(str(error))
                )

    def send_signed_transaction(self, transaction, attempts=10, wait_for_transaction_receipt=False):
        try:
            SingletonLock.instance().lock.acquire()
            return self.__send_signed_transaction(transaction, attempts, wait_for_transaction_receipt)
        finally:
            try:
                SingletonLock.instance().lock.release()
            except Exception as error:
                self.get_logger().debug(
                    "Error when releasing a lock in signed transaction {0}".format(str(error))
                )

    def __wait_for_confirmed_transaction_receipt(self, tx_hash):
        """
        Ensures that a transaction still exists in the blockchain after n blocks.
        Needed to avoid issues with uncle chains.
        Raises a Timeout exception if the transaction has disappeared or was never mined.
        """
        self.get_logger().debug("Waiting for an {}-blocks confirmation on the transaction".format(
            self.__n_blocks_confirmation
        ))

        __MAX_BLOCKS_FOR_CONFIRMATION = self.__n_blocks_confirmation * 3
        start_block = self.web3_client.eth.blockNumber
        current_block = self.web3_client.eth.blockNumber

        while current_block - start_block <= __MAX_BLOCKS_FOR_CONFIRMATION:
            current_block = self.web3_client.eth.blockNumber
            current_receipt = self.web3_client.eth.getTransactionReceipt(tx_hash)
            if current_receipt:
                tx_block_number = current_receipt["blockNumber"]
                if current_block - tx_block_number >= self.__n_blocks_confirmation:
                    self.get_logger().debug("Transaction has an {}-blocks confirmation.".format(
                        self.__n_blocks_confirmation
                    ))
                    return
            sleep(self.block_mined_polling_sec)

        self.get_logger().debug("Transaction could not be confirmed within {} blocks. Raising exception.".format(
                                __MAX_BLOCKS_FOR_CONFIRMATION))
    
        raise TransactionNotConfirmedException()


    def __send_signed_transaction(self, transaction, attempts=10, wait_for_transaction_receipt=False):
        args = self.mk_args()
        if self.__account.private_key is None:  # no local signing (in case of tests)
            return transaction.transact(args)
        else:
            nonce = self.web3_client.eth.getTransactionCount(self.__account.address)
            original_nonce = nonce
            for i in range(attempts):
                try:
                    args['nonce'] = nonce
                    tx = transaction.buildTransaction(args)
                    signed_tx = self.web3_client.eth.__account.signTransaction(tx, self.__account.private_key)
                    tx_hash = self.web3_client.eth.sendRawTransaction(signed_tx.rawTransaction)

                    if wait_for_transaction_receipt:
                        self.web3_client.eth.waitForTransactionReceipt(tx_hash, 120)
                        self.get_logger().debug("Transaction receipt found.")
                        if self.__n_blocks_confirmation > 0:
                            self.__wait_for_confirmed_transaction_receipt(tx_hash)
                    return tx_hash
                except ValueError as e:
                    if i == attempts - 1:
                        self.get_logger().debug("Maximum number of retries reached. {}".format(e))
                        raise e
                    elif "replacement transaction underpriced" in repr(e):
                        self.get_logger().debug("Another transaction is queued with the same nonce. {}".format(e))
                        nonce += 1
                    elif "nonce too low" in repr(e):
                        msg = "This nonce is too low {}. Web3 says transaction count is {}. " \
                            "The original nonce was {}. Error: {}".format(
                            nonce,
                            self.web3_client.eth.getTransactionCount(self.account.address),
                            original_nonce,
                            e)
                        self.get_logger().debug(msg)
                        nonce += 1
                    elif "known transaction" in repr(e):
                        # the de-duplication is preserved and the exception is re-raised
                        self.get_logger().debug("Transaction deduplication happened. {}".format(e))
                        raise DeduplicationException(e)
                    else:
                        self.get_logger().error("Unknown error while sending transaction. {}".format(e))

                except Timeout as e:
                    # If we time out after the default 120 seconds when waiting for a receipt,
                    # throw the exception to the calling thread.
                    # This is to avoid waiting indefinitely for an underpriced transaction.
                    raise e
                except TransactionNotConfirmedException as e:
                    # The transaction was found but then later uncled, and could not be confirmed.
                    raise e
