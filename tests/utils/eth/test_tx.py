####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import unittest

from web3.utils.threads import Timeout

from utils.eth.tx import mk_args, send_signed_transaction, make_read_only_call
from utils.eth.tx import DeduplicationException
from unittest.mock import Mock


class AccountMock:
    def __init__(self):
        self.signed_tx = None
        self.signed_private_key = None

    def signTransaction(self, tx, private_key):
        self.signed_private_key = private_key
        tx.sign()
        return tx


class EthMock:
    def __init__(self):
        self.account = AccountMock()
        self.transaction_sent = None

    def getTransactionCount(self, account_number):
        return 123

    def sendRawTransaction(self, tx):
        if tx.error_to_throw is not None:
            to_throw = tx.error_to_throw
            tx.error_to_throw = None
            raise to_throw
        return tx


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
    def __init__(self, value, exception):
        self.value = value
        self.exception = exception

    def call(self, *args):
        if self.exception is None:
            return self.value
        raise self.exception


class TestFile(unittest.TestCase):

    @staticmethod
    def get_config_mock(gas_price_wei, gas, private_key=None):
        mock = Mock()
        mock.gas = gas
        mock.gas_price_wei = gas_price_wei
        mock.account = "account"
        mock.account_private_key = private_key
        mock.web3_client.eth = EthMock()
        mock.logger = Mock()
        return mock

    def test_mk_args_none_gas(self):
        """
        If no gas is provided, the arguments do not contain the gas record.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, None)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        try:
            temp = result['gas']
            self.fail("The gas record should not be contained in the dictionary")
        except KeyError:
            # Expected
            pass

    def test_mk_args_zero_gas(self):
        """
        Tests zero gas case.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, 0)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(0, result['gas'])

    def test_mk_args_positive_gas(self):
        """
        Tests positive gas case.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, 7)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_mk_args_string_gas(self):
        """
        Tests positive gas case where gas is provided as a string.
        """
        gas_price_wei = 4000000000
        config = TestFile.get_config_mock(gas_price_wei, '7')
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_mk_args_negative_gas(self):
        """
        Tests negative gas case provided as string. The value should not be included.
        """
        config = TestFile.get_config_mock(4000000000, '-8')
        try:
            mk_args(config)
        except ValueError:
            # Expected
            pass

    def test_make_read_only_call(self):
        """
        Tests that the method returns a value if a value is returned, and raises an exception if an
        exception is raised by the call.
        """
        error = ValueError("unknown error")
        read_only = ReadOnlyMethodMock(15, None)
        config = TestFile.get_config_mock(4000000000, 0)
        self.assertEquals(15, make_read_only_call(config, read_only))
        read_only = ReadOnlyMethodMock(15, error)
        try:
            make_read_only_call(config, read_only)
            self.fail("An error was expected")
        except ValueError as e:
            self.assertTrue(e is error)

    def test_send_signed_transaction_local_signing_with_unknown_error(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("unknown error")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        try:
            send_signed_transaction(config, transaction)
            self.fail("An error was expected")
        except ValueError as e:
            self.assertTrue(e is error)

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_signing_with_known_transaction(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("known transaction")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        try:
            send_signed_transaction(config, transaction)
            self.fail("An error was expected")
        except DeduplicationException as e:
            # the error is supposed to be re-raised for de-duplication, but wrapped
            # as DeduplicationException instead of ValueError
            pass

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_signing_with_replacement(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("replacement transaction underpriced")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        # the nonce has been incremented once
        self.assertEqual(124, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_local_signing_with_low_nonce(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("replacement transaction underpriced")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        # the nonce has been incremented once
        self.assertEqual(124, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_local_signing_out_of_retries(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = ValueError("replacement transaction underpriced")
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        try:
            send_signed_transaction(config, transaction, attempts=1)
            self.fail("An error was expected")
        except ValueError as e:
            # the error is supposed to be re-raised because we are out of retries
            self.assertTrue(e is error)

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_timeout(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        error = Timeout()
        transaction = SimpleTransactionMock(error_to_throw=error)
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        try:
            send_signed_transaction(config, transaction, attempts=1)
            self.fail("An error was expected")
        except Timeout as e:
            # the error is supposed to be re-raised because we are out of retries
            self.assertTrue(e is error)

        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)

    def test_send_signed_transaction_local_signing(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0, private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_remote_signing(self):
        """
        Tests the case when the transaction is not signed locally (when the private key is not
        provided).
        """
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = TestFile.get_config_mock(4000000000, 0)
        result = send_signed_transaction(config, transaction)

        self.assertFalse(result.is_signed)
        self.assertIsNone(config.web3_client.eth.account.signed_private_key)
        self.assertIsNone(result.build_args)
        self.assertEqual(mk_args(config), result.transact_args)
