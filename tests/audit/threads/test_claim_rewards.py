####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from time import sleep
from unittest import mock
from unittest.mock import MagicMock
from web3.utils.threads import Timeout

from audit import ClaimRewardsThread
from helpers.resource import fetch_config, remove
from helpers.qsp_test import QSPTest
from timeout_decorator import timeout
from utils.eth import DeduplicationException


class TestClaimRewards(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config(inject_contract=True)
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config(inject_contract=True)
        self.__claim_rewards_thread = ClaimRewardsThread(self.__config)

    def test_init(self):
        self.assertEqual(self.__config, self.__claim_rewards_thread.config)

    @timeout(15, timeout_exception=StopIteration)
    def test_start_stop(self):
        # start the thread, signal stop and exit. use mock not to make work
        with mock.patch('audit.threads.claim_rewards_thread.send_signed_transaction',
                        return_value="hash"), \
             mock.patch('audit.threads.claim_rewards_thread.mk_read_only_call',
                        return_value=False):
            self.__claim_rewards_thread.start()
            while not self.__claim_rewards_thread.exec:
                sleep(0.1)
            self.__claim_rewards_thread.stop()
            self.assertFalse(self.__claim_rewards_thread.exec)

    def test_call_to_claim_rewards_no_exception(self):
        """
        Tests whether calling the smart contract to claim rewards works without throwing an
        exception.
        """
        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards()

    def test_call_to_has_available_rewards_no_exception_XXX(self):
        """
        Tests whether calling the smart contract to check for available rewards works without
        throwing an exception.
        """
        self.__claim_rewards_thread._ClaimRewardsThread__has_available_rewards()

    def test_claim_rewards_when_no_rewards_available(self):
        """
        Tests whether the __claim_rewards_if_available function invokes __claim_rewards
        when rewards are NOT available.
        """
        self.__claim_rewards_thread._ClaimRewardsThread__has_available_rewards = MagicMock()
        self.__claim_rewards_thread._ClaimRewardsThread__has_available_rewards.return_value = False

        claim_rewards = MagicMock()
        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards = claim_rewards

        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards_if_available()
        claim_rewards.assert_not_called()

    def test_claim_rewards_when_rewards_available(self):
        """
        Tests whether the __claim_rewards_if_available function invokes __claim_rewards
        when rewards are available.
        """
        # simulates the while-loop iterating once
        has_rewards_generator = iter([True, False])

        def has_available_rewards():
            return next(has_rewards_generator)

        self.__claim_rewards_thread._exec = True

        self.__claim_rewards_thread._ClaimRewardsThread__has_available_rewards = \
            has_available_rewards

        claim_rewards = MagicMock()
        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards = claim_rewards

        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards_if_available()
        claim_rewards.assert_called()
        self.__claim_rewards_thread._exec = False

    def test_claim_rewards_when_many_rewards_available(self):
        """
        Tests whether the __claim_rewards_if_available function invokes __claim_rewards
        when rewards are available.
        """
        # simulates the while-loop iterating multiple times
        has_rewards_generator = iter([True, True, False])

        def has_available_rewards():
            return next(has_rewards_generator)

        self.__claim_rewards_thread._exec = True
        self.__claim_rewards_thread._ClaimRewardsThread__has_available_rewards = \
            has_available_rewards

        claim_rewards = MagicMock()
        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards = claim_rewards

        self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards_if_available()
        claim_rewards.assert_called()
        self.__claim_rewards_thread._exec = False

    def test_claim_rewards_timeout_exception(self):
        """
        Tests whether a timeout exception is thrown when the __claim_rewards function
        transaction timeouts.
        """
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch(
                'audit.threads.claim_rewards_thread.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = Timeout()
                self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards()
                self.fail("An exception should have been thrown")
            except Timeout:
                pass

    def test_claim_rewards_deduplication_exception(self):
        """
        Tests whether a deduplication exception is thrown when the __claim_rewards function
        transaction has not been mined yet.
        """
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch(
                'audit.threads.claim_rewards_thread.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = DeduplicationException()
                self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards()
                self.fail("An exception should have been thrown")
            except DeduplicationException:
                pass

    def test_claim_rewards_other_exception(self):
        """
        Tests whether an exception is thrown when the __claim_rewards when an
        unexpected error occurs.
        """
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch(
                'audit.threads.claim_rewards_thread.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = ValueError()
                self.__claim_rewards_thread._ClaimRewardsThread__claim_rewards()
                self.fail("An exception should have been thrown")
            except ValueError:
                pass

    def tearDown(self):
        if self.__claim_rewards_thread.exec:
            self.__claim_rewards_thread.stop()

        remove(self.__config.evt_db_path)
