import unittest

from utils.eth.tx import mk_args


class SimpleConfigMock():

    def __init__(self, default_gas):
        self.__default_gas = default_gas
        self.__account = "account"

    @property
    def default_gas(self):
        return self.__default_gas

    @property
    def account(self):
        return self.__account


class TestFile(unittest.TestCase):

    def test_none_gas(self):
        config = SimpleConfigMock(None)
        result = mk_args(config)
        self.assertEqual(0, result['gasPrice'])
        self.assertEqual('account', result['from'])
        try:
            temp = result['gas']
            self.fail("The gas record should not be contained in the dictionary")
        except KeyError:
            # Expected
            pass

    def test_zero_gas(self):
        config = SimpleConfigMock(0)
        result = mk_args(config)
        self.assertEqual(0, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(0, result['gas'])

    def test_positive_gas(self):
        config = SimpleConfigMock(7)
        result = mk_args(config)
        self.assertEqual(0, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_string_gas(self):
        config = SimpleConfigMock('7')
        result = mk_args(config)
        self.assertEqual(0, result['gasPrice'])
        self.assertEqual('account', result['from'])
        self.assertEqual(7, result['gas'])

    def test_negative_gas(self):
        config = SimpleConfigMock('-8')
        result = mk_args(config)
        self.assertEqual(0, result['gasPrice'])
        self.assertEqual('account', result['from'])
        try:
            temp = result['gas']
            self.fail("The gas record should not be contained in the dictionary")
        except KeyError:
            # Expected
            pass
