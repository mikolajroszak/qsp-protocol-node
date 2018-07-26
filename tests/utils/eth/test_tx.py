import unittest

from utils.eth.tx import mk_args, send_signed_transaction


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
        return tx


class Web3ClientMock:
    def __init__(self):
        self.eth = EthMock()


class SimpleTransactionMock:
    def __init__(self):
        self.transact_args = None
        self.build_args = None
        self.__is_signed = False

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


class SimpleConfigMock:
    def __init__(self, gas_price_wei, gas, private_key=None):
        self.__gas_price_wei = gas_price_wei
        self.__gas = gas
        self.__account = "account"
        self.__account_private_key = private_key
        self.__web3_client = Web3ClientMock()

    @property
    def gas_price_wei(self):
        return self.__gas_price_wei

    @property
    def gas(self):
        return self.__gas

    @property
    def account(self):
        return self.__account

    @property
    def account_private_key(self):
        return self.__account_private_key

    @property
    def web3_client(self):
        return self.__web3_client


class TestFile(unittest.TestCase):

    def test_mk_args_none_gas(self):
        """
        If no gas is provided, the arguments do not contain the gas record.
        """
        gas_price_wei = 4000000000
        config = SimpleConfigMock(gas_price_wei, None)
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
        config = SimpleConfigMock(gas_price_wei, 0)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(0, result['gas'])

    def test_mk_args_positive_gas(self):
        """
        Tests positive gas case.
        """
        gas_price_wei = 4000000000
        config = SimpleConfigMock(gas_price_wei, 7)
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_mk_args_string_gas(self):
        """
        Tests positive gas case where gas is provided as a string.
        """
        gas_price_wei = 4000000000
        config = SimpleConfigMock(gas_price_wei, '7')
        result = mk_args(config)
        self.assertEqual(gas_price_wei, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_mk_args_negative_gas(self):
        """
        Tests negative gas case provided as string. The value should not be included.
        """
        config = SimpleConfigMock(4000000000, '-8')
        try:
            mk_args(config)
        except ValueError:
            # Expected
            pass

    def test_send_signed_transaction_local_signing(self):
        """
        Tests the case when the transaction is signed locally (the private key is provided).
        """
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = SimpleConfigMock(4000000000, 0, private_key)
        result = send_signed_transaction(config, transaction)

        self.assertTrue(result.is_signed)
        self.assertEqual(private_key, config.web3_client.eth.account.signed_private_key)
        self.assertEqual(123, result.build_args['nonce'])
        self.assertIsNone(result.transact_args)

    def test_send_signed_transaction_remote_signing(self):
        """
        Tests the case when the transaction is not signed locally (when the private key is not provided).
        """
        transaction = SimpleTransactionMock()
        private_key = "abc"
        config = SimpleConfigMock(4000000000, 0)
        result = send_signed_transaction(config, transaction)

        self.assertFalse(result.is_signed)
        self.assertIsNone(config.web3_client.eth.account.signed_private_key)
        self.assertIsNone(result.build_args)
        self.assertEqual(mk_args(config), result.transact_args)
