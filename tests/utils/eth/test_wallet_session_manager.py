import unittest

from utils.eth.wallet_session_manager import WalletSessionManager


class FunctionCall:

    def __init__(self, function_name, params, return_value):
        self.params = params
        self.function_name = function_name
        self.return_value = return_value

    def __str__(self):
        return self.function_name

    def __repr__(self):
        return self.function_name


class Web3ClientPersonalMock:
    """
    A mock class used as stub for the internals of the Web3 provider.
    """

    def __init__(self):
        self.expected = []

    def expect(self, function, params, return_value):
        """
        Adds an expected function call to the queue.
        """
        self.expected.append(FunctionCall(function, params, return_value))

    def verify(self):
        """
        Verifies that all the expected calls were performed.
        """
        if len(self.expected) != 0:
            raise Exception('Some excpected calls were left over: ' + str(self.expected))

    def unlockAccount(self, account, passwd, ttl):
        """
        A stub for the unlockAccount method.
        """
        first_call = self.expected[0]
        if first_call.function_name != 'unlockAccount':
            raise Exception('unlockAccount call expected')
        if first_call.params['account'] != account:
            raise Exception('Value of account is not as expected: ' + str(account))
        if first_call.params['passwd'] != passwd:
            raise Exception('Value of passwd is not as expected: ' + str(passwd))
        if first_call.params['ttl'] != ttl:
            raise Exception('Value of ttl is not as expected: ' + str(ttl))
        self.expected = self.expected[1:]
        return first_call.return_value

    def lockAccount(self, account):
        """
        A stub for the lock method.
        """
        first_call = self.expected[0]
        if first_call.function_name != 'lockAccount':
            raise Exception('lockAccount call expected')
        if first_call.params['account'] != account:
            raise Exception('Value of account is not as expected: ' + str(account))
        self.expected = self.expected[1:]
        return first_call.return_value


class Web3ClientMock:

    def __init__(self):
        self.personal = Web3ClientPersonalMock()


class TestWalletSessionManager(unittest.TestCase):
    ACCOUNT = 'act_name'
    CLIENT = 'client'
    PASSWD = 'passwd'
    TTL = 15

    def test_init(self):
        """
        Tests that the values are properly assigned to internal attributes.
        """
        manager = WalletSessionManager(TestWalletSessionManager.CLIENT,
                                       TestWalletSessionManager.ACCOUNT,
                                       TestWalletSessionManager.PASSWD)
        self.assertEqual(TestWalletSessionManager.CLIENT,
                         manager._WalletSessionManager__web3_client)
        self.assertEqual(TestWalletSessionManager.ACCOUNT, manager._WalletSessionManager__account)
        self.assertEqual(TestWalletSessionManager.PASSWD, manager._WalletSessionManager__passwd)

    def test_unlock(self):
        """
        Tests that the unlock calls are properly delegated.
        """
        mock = Web3ClientMock()
        manager = WalletSessionManager(mock,
                                       TestWalletSessionManager.ACCOUNT,
                                       TestWalletSessionManager.PASSWD)
        mock.personal.expect('unlockAccount', {'account': TestWalletSessionManager.ACCOUNT,
                                               'passwd': TestWalletSessionManager.PASSWD,
                                               'ttl': TestWalletSessionManager.TTL}, True)
        manager.unlock(TestWalletSessionManager.TTL)
        mock.personal.verify()

    def test_unlock_with_exception(self):
        """
        Tests that the unlock calls are properly delegated and an exception is raised if they fail.
        """
        mock = Web3ClientMock()
        manager = WalletSessionManager(mock,
                                       TestWalletSessionManager.ACCOUNT,
                                       TestWalletSessionManager.PASSWD)
        mock.personal.expect('unlockAccount', {'account': TestWalletSessionManager.ACCOUNT,
                                               'passwd': TestWalletSessionManager.PASSWD,
                                               'ttl': TestWalletSessionManager.TTL}, False)
        try:
            manager.unlock(TestWalletSessionManager.TTL)
            self.fail("An exception is expected on failed unlock")
        except Exception:
            # Expected
            pass
        mock.personal.verify()

    def test_lock(self):
        """
        Tests the lock calls are properly delegated
        """
        mock = Web3ClientMock()
        manager = WalletSessionManager(mock,
                                       TestWalletSessionManager.ACCOUNT,
                                       TestWalletSessionManager.PASSWD)
        mock.personal.expect('lockAccount', {'account': TestWalletSessionManager.ACCOUNT}, None)
        result = manager.lock()
        self.assertIsNone(result)
        mock.personal.verify()
