####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

import itertools

from web3.utils.threads import Timeout

from helpers.qsp_test import QSPTest
from utils.eth.tx import mk_args, send_signed_transaction, mk_read_only_call, TransactionNotConfirmedException
from utils.eth.tx import DeduplicationException
from unittest.mock import Mock, patch


class AccountMock:
    def __init__(self):
        self.signed_tx = None
        self.signed_private_key = None

    def signTransaction(self, tx, private_key):
        self.signed_private_key = private_key
        tx.sign()
        return tx


class EthMock:
    def __init__(self, repeat=False, receipt_generator=None, block_generator=None):
        self.account = AccountMock()
        self.transaction_sent = None
        self.repeat = repeat
        # simulate changing receipts and block numbers with iterables
        if not receipt_generator:
            receipt_generator = itertools.repeat({"blockNumber": 1, "blockHash": 2}, 100000)
        self.receipt_generator = receipt_generator
        if not block_generator:
            block_generator = iter(range(1, 100000))
        self.block_generator = block_generator

    def getTransactionCount(self, account_number):
        return 123

    def sendRawTransaction(self, tx):
        if tx.error_to_throw is not None:
            to_throw = tx.error_to_throw
            if not self.repeat:
                tx.error_to_throw = None
            raise to_throw
        return tx

    def waitForTransactionReceipt(self, tx_hash, timeout):
        return next(self.receipt_generator)

    def getTransactionReceipt(self, tx_hash):
        return next(self.receipt_generator)

    @property
    def blockNumber(self):
        return next(self.block_generator)

    @property
    def defaultAccount(self):
        return self.account


class SimpleTransactionMock:
    def __init__(self, error_to_throw=None):
        self.transact_args = None
        self.build_args = None
        self.__is_signed = False
        self.error_to_throw = error_to_throw

    def buildTransaction(self, args):
        self.build_args = args
        return self

    def transact(self, args):
        self.transact_args = args
        return self

    @property
    def rawTransaction(self):
        return self

    def sign(self):
        self.__is_signed = True

    @property
    def is_signed(self):
        return self.__is_signed


class ReadOnlyMethodMock:
    def __init__(self, value, exception, address):
        self.value = value
        self.exception = exception
        self.address = address


def __method_call(method, unused1, unused2):
    if method.exception is None:
        return method.value
    raise method.exception


@patch('utils.eth.tx.__method_call', side_effect=__method_call)
class TestFile(QSPTest):

    @staticmethod
    def get_config_mock(gas_price_wei,
                        gas_limit,
                        n_blocks_confirmation=6,
                        private_key=None,
                        repeat=False,
                        receipt_generator=None,
                        block_generator=None):
        mock = Mock()
        mock.gas_limit = gas_limit
        mock.gas_price_wei = gas_price_wei
        mock.n_blocks_confirmation = n_blocks_confirmation
        mock.account = "account"
        mock.account_private_key = private_key
        mock.web3_client.eth = EthMock(repeat=repeat,
                                       receipt_generator=receipt_generator,
                                       block_generator=block_generator)
        mock.logger = Mock()
        mock.block_mined_polling = 0.1

        return mock

    def test_mk_args_none_gas(self, method_call_mock):
        """
        If no gas is provided, the arguments do not contain the gas record.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, None)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertTrue('gas' not in result)

    def test_mk_args_zero_gas(self, method_call_mock):
        """
        Tests zero gas case.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, 0)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(0, result['gas'])

    def test_mk_args_positive_gas(self, method_call_mock):
        """
        Tests positive gas case.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, 7)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_mk_args_string_gas(self, method_call_mock):
        """
        Tests positive gas case where gas is provided as a string.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, '7')
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_mk_args_negative_gas(self, method_call_mock):
        """
        Tests negative gas case provided as string. The value should not be included.
        """
        config = TestFile.get_config_mock(4000000000, '-8')
        try:
            mk_args(config)
        except ValueError:
            # Expected
            pass

    def test_mk_read_only_call(self, method_call_mock):
        """
        Tests that the method returns a value if a value is returned, and raises an exception if an
        exception is raised by the call.
        """
        error = ValueError("unknown error")
        address = "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"
        read_only = ReadOnlyMethodMock(15, None, address)
        config = TestFile.get_config_mock(4000000000, 0)
        self.assertEquals(15, mk_read_only_call(config, read_only))
        read_only = ReadOnlyMethodMock(15, error, address)
        try:
            mk_read_only_call(config, read_only)
            self.fail("An error was expected")
        except ValueError as e:
            self.assertTrue(e is error)

    def test_send_signed_transaction_local_signing_with_unknown_error(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("unknown error")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key, repeat=True)
        try:
            send_signed_transaction(config, transaction)
            self.fail("An error was expected")
        except ValueError as e:
            self.assertTrue(e is error)

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_signing_with_known_transaction(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("known transaction")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key)
        try:
            send_signed_transaction(config, transaction)
            self.fail("An error was expected")
        except DeduplicationException:
            # the error is supposed to be re-raised for de-duplication, but wrapped
            # as DeduplicationException instead of ValueError
            pass

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_signing_with_replacement(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("replacement transaction underpriced")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        # the nonce has been incremented once
        self.assertEqual(124, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_local_signing_with_low_nonce(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("replacement transaction underpriced")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        # the nonce has been incremented once
        self.assertEqual(124, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_local_signing_out_of_retries(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("replacement transaction underpriced")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key)
        try:
            send_signed_transaction(config, transaction, attempts=1)
            self.fail("An error was expected")
        except ValueError as e:
            # the error is supposed to be re-raised because we are out of retries
            self.assertTrue(e is error)

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_timeout(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = Timeout()
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key)
        try:
            send_signed_transaction(config, transaction, attempts=1)
            self.fail("An error was expected")
        except Timeout as e:
            # the error is supposed to be re-raised because we are out of retries
            self.assertTrue(e is error)

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_signing(self, method_call_mock):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key=private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_remote_signing(self, method_call_mock):
        """
        Tests the case when the transaction is not signed locally (when the private key is not
        provided).
        """
        transaction = SimpleTransactionMock()
        config = TestFile.get_config_mock(4000000000, 0)
        result = send_signed_transaction(config, transaction)

        self.assertFalse(result.is_signed)
        self.assertIsNone(config.web3_client.eth.account.signed_private_key)
        self.assertIsNone(result.build_args)
        self.assertEqual(mk_args(config), result.transact_args)

    def test_wait_for_confirmed_transaction_receipt_basic_confirmation(self, method_call_mock):
        gas_price_wei = 4000000000
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(gas_price_wei,
                                          1,
                                          private_key=private_key
                                          )
        result = send_signed_transaction(config,
                                         transaction,
                                         wait_for_transaction_receipt=True)
        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_wait_for_confirmed_transaction_receipt_confirmation_with_slowed_block_time(self, method_call_mock):
        gas_price_wei = 4000000000
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(gas_price_wei,
                                          1,
                                          private_key=private_key,
                                          block_generator=itertools.chain(
                                              itertools.repeat(1, 10),
                                              range(2, 1000000)
                                          ),
                                          )
        result = send_signed_transaction(config,
                                         transaction,
                                         wait_for_transaction_receipt=True)
        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_wait_for_confirmed_transaction_receipt_confirmation_uncled_once(self, method_call_mock):
        gas_price_wei = 4000000000
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(gas_price_wei,
                                          1,
                                          private_key=private_key,
                                          receipt_generator=itertools.chain(
                                              itertools.repeat({
                                                  "blockNumber": 1,
                                                  "blockHash": 2},
                                                  3),
                                              itertools.repeat({
                                                  "blockNumber": 3,
                                                  "blockHash": 4},
                                                  1000000)
                                          ))
        result = send_signed_transaction(config,
                                         transaction,
                                         wait_for_transaction_receipt=True)
        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_wait_for_confirmed_transaction_receipt_confirmation_orphaned_once(self, method_call_mock):
        gas_price_wei = 4000000000
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(gas_price_wei,
                                          1,
                                          private_key=private_key,
                                          receipt_generator=itertools.chain(
                                              itertools.repeat({
                                                  "blockNumber": 1,
                                                  "blockHash": 2},
                                                  3),
                                              itertools.repeat(None, 1),
                                              itertools.repeat({
                                                  "blockNumber": 3,
                                                  "blockHash": 4},
                                                  1000000)
                                          ))
        result = send_signed_transaction(config,
                                         transaction,
                                         wait_for_transaction_receipt=True)
        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_wait_for_confirmed_transaction_receipt_exceeded_max_confirmation_timeout(self, method_call_mock):
        error_occurred = False
        gas_price_wei = 4000000000
        transaction = SimpleTransactionMock()
        private_key = "abc"
        receipt_generator = iter([{"blockNumber": i, "blockHash": i + 1} for i in range(1000000)])
        config = TestFile.get_config_mock(gas_price_wei,
                                          1,
                                          private_key=private_key,
                                          receipt_generator=receipt_generator
                                          )
        try:
            send_signed_transaction(config,
                                    transaction,
                                    wait_for_transaction_receipt=True)
            self.fail("An error was expected")
        except TransactionNotConfirmedException:
            # the error is supposed to be re-raised because we are out of retries
            error_occurred = True
        self.assertTrue(error_occurred)
