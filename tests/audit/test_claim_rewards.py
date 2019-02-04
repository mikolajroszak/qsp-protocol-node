from unittest import mock
from unittest.mock import MagicMock
from web3.utils.threads import Timeout

from audit import QSPAuditNode
from helpers.resource import fetch_config, remove
from helpers.qsp_test import QSPTest
from utils.eth import DeduplicationException


class TestClaimRewardFunctions(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config()
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config()
        self.__audit_node = QSPAuditNode(self.__config)

    def test_call_to_claim_rewards(self):
        """
        Tests whether calling the smart contract to claim rewards works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__claim_rewards()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_call_to_has_available_rewards(self):
        """
        Tests whether calling the smart contract to check for available rewards works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__has_available_rewards()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_claim_rewards_when_no_rewards_available(self):
        """
        Tests whether the __claim_rewards_if_available function invokes __claim_rewards
        when rewards are NOT available.
        """
        self.__audit_node._QSPAuditNode__has_available_rewards = MagicMock()
        self.__audit_node._QSPAuditNode__has_available_rewards.return_value = False

        claim_rewards = MagicMock()
        self.__audit_node._QSPAuditNode__claim_rewards = claim_rewards

        self.__audit_node._QSPAuditNode__claim_rewards_if_available()
        claim_rewards.assert_not_called()

    def test_claim_rewards_when_rewards_available(self):
        """
        Tests whether the __claim_rewards_if_available function invokes __claim_rewards
        when rewards are available.
        """
        self.__audit_node._QSPAuditNode__has_available_rewards = MagicMock()
        self.__audit_node._QSPAuditNode__has_available_rewards.return_value = True

        claim_rewards = MagicMock()
        self.__audit_node._QSPAuditNode__claim_rewards = claim_rewards

        self.__audit_node._QSPAuditNode__claim_rewards_if_available()
        claim_rewards.assert_called()

    def test_claim_rewards_timeout_exception(self):
        """
        Tests whether a timeout exception is thrown when the __claim_rewards function
        transaction timeouts.
        """
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = Timeout()
                self.__audit_node._QSPAuditNode__claim_rewards()
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
        with mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = DeduplicationException()
                self.__audit_node._QSPAuditNode__claim_rewards()
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
        with mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = ValueError()
                self.__audit_node._QSPAuditNode__claim_rewards()
                self.fail("An exception should have been thrown")
            except ValueError:
                pass

    def tearDown(self):
        if self.__audit_node._QSPAuditNode__exec:
            self.__audit_node.stop()

        remove(self.__config.evt_db_path)
