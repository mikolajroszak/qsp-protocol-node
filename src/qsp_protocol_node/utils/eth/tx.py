####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################
from time import sleep

from log_streaming import get_logger
from .singleton_lock import SingletonLock

from web3.utils.threads import Timeout

logger = get_logger(__name__)


def mk_args(config):
    gas_limit = config.gas_limit
    gas_price_wei = config.gas_price_wei
    if gas_limit is None:
        args = {'from': config.account, 'gasPrice': gas_price_wei}
    else:
        gas_value = int(gas_limit)
        if gas_value >= 0:
            args = {'from': config.account, 'gas': gas_value, 'gasPrice': gas_price_wei}
        else:
            raise ValueError("The gas value is negative: " + str(gas_value))

    return args


def mk_read_only_call(config, method):
    try:
        SingletonLock.instance().lock.acquire()
        return method.call({'from': config.account})
    finally:
        try:
            SingletonLock.instance().lock.release()
        except Exception as error:
            logger.debug(
                "Error when releasing a lock in a read-only call transaction {0}".format(str(error))
            )


def get_gas_price(config):
    try:
        SingletonLock.instance().lock.acquire()
        return config.web3_client.eth.gasPrice
    finally:
        try:
            SingletonLock.instance().lock.release()
        except Exception as error:
            config.logger.debug(
                "Error when releasing a lock in gas price read {0}".format(str(error))
            )


def send_signed_transaction(config, transaction, attempts=10, wait_for_transaction_receipt=False):
    try:
        SingletonLock.instance().lock.acquire()
        return __send_signed_transaction(config,
                                         transaction,
                                         attempts,
                                         wait_for_transaction_receipt)
    finally:
        try:
            SingletonLock.instance().lock.release()
        except Exception as error:
            logger.debug(
                "Error when releasing a lock in signed transaction {0}".format(str(error))
            )


def __wait_for_confirmed_transaction_receipt(config, tx_hash):
    """
    Ensures that a transaction still exists in the blockchain after n blocks.
    Needed to avoid issues with uncle chains.
    Raises a Timeout exception if the transaction has disappeared or was never mined.
    """
    logger.debug("Waiting for {}-blocks confirmation on the transaction".format(
        config.n_blocks_confirmation
    ))

    __MAX_BLOCKS_FOR_CONFIRMATION = config.n_blocks_confirmation * 3
    start_block = config.web3_client.eth.blockNumber
    current_block = config.web3_client.eth.blockNumber

    while current_block - start_block <= __MAX_BLOCKS_FOR_CONFIRMATION:
        current_block = config.web3_client.eth.blockNumber
        current_receipt = config.web3_client.eth.getTransactionReceipt(tx_hash)
        if current_receipt:
            tx_block_number = current_receipt["blockNumber"]
            if current_block - tx_block_number >= config.n_blocks_confirmation:
                logger.debug("Transaction has {}-blocks confirmation.".format(
                    config.n_blocks_confirmation
                ))
                return
        sleep(config.block_mined_polling)

    logger.debug("Transaction could not be confirmed within {} blocks. Raising exception.".format(
        __MAX_BLOCKS_FOR_CONFIRMATION))
    raise TransactionNotConfirmedException()


def __log_tx_failure(tx_receipt):
    """
    Makes a log record at error level when a transaction fails.
    """
    if tx_receipt is None:
        logger.debug("Cannot check status of transaction with None receipt.")
    else:
        try:
            if not bool(tx_receipt["status"]):
                logger.error("Transaction failed: {0}".format(str(tx_receipt)))
        except KeyError:
            logger.error("Status is not available in receipt: {0}".format(str(tx_receipt)))


def __send_signed_transaction(config, transaction, attempts=10, wait_for_transaction_receipt=False):
    args = mk_args(config)
    if config.account_private_key is None:  # no local signing (in case of tests)
        return transaction.transact(args)
    else:
        nonce = config.web3_client.eth.getTransactionCount(config.account)
        original_nonce = nonce
        for i in range(attempts):
            try:
                args['nonce'] = nonce
                tx = transaction.buildTransaction(args)
                signed_tx = config.web3_client.eth.account.signTransaction(tx,
                                                                           private_key=config.account_private_key)
                tx_hash = config.web3_client.eth.sendRawTransaction(signed_tx.rawTransaction)

                if wait_for_transaction_receipt:
                    receipt = config.web3_client.eth.waitForTransactionReceipt(tx_hash, 120)
                    logger.debug("Transaction receipt found.")
                    if config.n_blocks_confirmation > 0:
                        __wait_for_confirmed_transaction_receipt(config, tx_hash)
                    __log_tx_failure(receipt)
                return tx_hash
            except ValueError as e:
                if i == attempts - 1:
                    logger.debug("Maximum number of retries reached. {}".format(e))
                    raise e
                elif "replacement transaction underpriced" in repr(e):
                    logger.debug("Another transaction is queued with the same nonce. {}".format(e))
                    nonce += 1
                elif "nonce too low" in repr(e):
                    msg = "This nonce is too low {}. Web3 says transaction count is {}. " \
                          "The original nonce was {}. Error: {}".format(
                        nonce,
                        config.web3_client.eth.getTransactionCount(config.account),
                        original_nonce,
                        e)
                    logger.debug(msg)
                    nonce += 1
                elif "known transaction" in repr(e):
                    # the de-duplication is preserved and the exception is re-raised
                    logger.debug("Transaction deduplication happened. {}".format(e))
                    raise DeduplicationException(e)
                else:
                    logger.error("Unknown error while sending transaction. {}".format(e))

            except Timeout as e:
                # If we time out after the default 120 seconds when waiting for a receipt,
                # throw the exception to the calling thread.
                # This is to avoid waiting indefinitely for an underpriced transaction.
                raise e
            except TransactionNotConfirmedException as e:
                # The transaction was found but then later uncled, and could not be confirmed.
                raise e


class DeduplicationException(Exception):
    pass


class TransactionNotConfirmedException(Exception):
    pass
