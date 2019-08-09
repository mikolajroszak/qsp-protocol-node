####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from audit import PollRequestsThread, BlockMinedPollingThread
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config, remove
from timeout_decorator import timeout
from unittest import mock
from utils.eth import DeduplicationException
from unittest.mock import MagicMock

from time import sleep


class TestPollRequestsThread(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config(inject_contract=True)
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config(inject_contract=True)
        self.__block_mined_polling_thread = BlockMinedPollingThread(self.__config)
        self.__poll_requests_thread = PollRequestsThread(self.__config, self.__block_mined_polling_thread)

    def test_init(self):
        config = fetch_config(inject_contract=True)
        thread = PollRequestsThread(config, self.__block_mined_polling_thread)
        self.assertEqual(config, thread.config)

    def test_call_to_get_next_police_assignment(self):
        """
        Tests whether calling the smart contract to get the next police
        assigment works.
        """
        exception = None
        try:
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            poll_requests_instance._PollRequestsThread__get_next_police_assignment()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_non_police_cannot_poll_check_events(self):
        self.__test_police_poll_event(
            is_police=False,
            is_new_assignment=False,
            is_already_processed=False,
            should_add_evt=False
        )

    def test_police_does_not_save_evt_upon_no_request(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=False,
            is_already_processed=False,
            should_add_evt=False
        )

    def test_police_does_not_save_evt_upon_repeated_request(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=True,
            is_already_processed=True,
            should_add_evt=False
        )

    def test_police_saves_evt_upon_new_request(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=True,
            is_already_processed=False,
            should_add_evt=True
        )

    def test_police_does_not_save_evt_when_not_confirmed(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=True,
            is_already_processed=True,
            should_add_evt=False,
            is_confirmed=False
        )

    def test_qsp_return_in_get_min_stake_audit(self):
        """
        Tests whether the conversion in get_min_stake_audit works, return
        a result in QSP.
        """
        with mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                   return_value=(1000 * (10 ** 18))):
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            min_stake = poll_requests_instance._PollRequestsThread__get_min_stake_qsp()

            self.assertEquals(min_stake, 1000)

    def test_call_to_get_min_stake_audit(self):
        """
        Tests whether calling the smart contract works.
        """
        exception = None
        try:
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            poll_requests_instance._PollRequestsThread__get_min_stake_qsp()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    @timeout(10, timeout_exception=StopIteration)
    def test_poll_audit_request_exception(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)

        def mocked__get_next_audit_request():
            raise Exception('mocked exception')

        poll_requests_instance._PollRequestsThread__get_next_audit_request = \
            mocked__get_next_audit_request
        # any request available is 1
        with mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                   return_value=1):
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            self.assert_event_table_contains(self.__config, [])

    @timeout(10, timeout_exception=StopIteration)
    def test_call_to_poll_audit_request_when_disabled_as_police(self):
        """
        Tests that calling poll_audit_requests exits if a police node calls it when disabled.
        """
        with mock.patch('audit.audit.QSPAuditNode.is_police_officer', return_value=True), \
             mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                        return_value=0) as mk_read_only_call:
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            mk_read_only_call.assert_not_called()

    @timeout(10, timeout_exception=StopIteration)
    def test_call_to_poll_audit_request_when_disabled_as_regular_node(self):
        """
        Tests that calling poll_audit_requests executes if a regular node calls it when
        the police node audit option is disabled.
        """
        with mock.patch('audit.audit.QSPAuditNode.is_police_officer', return_value=False), \
             mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                        return_value=0) as mk_read_only_call:
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            mk_read_only_call.assert_called()

    @timeout(10, timeout_exception=StopIteration)
    def test_call_to_poll_audit_request_when_enabled_as_police_node(self):
        """
        Tests that calling poll_audit_requests executes if a police node calls it when
        the police node audit option is enabled.
        """
        with mock.patch('audit.audit.QSPAuditNode.is_police_officer', return_value=True), \
             mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                        return_value=0) as mk_read_only_call:
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            poll_requests_instance.config._Config__enable_police_audit_polling = True
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            # the function call is going to fail, but we only care about whether
            # this function will be called
            mk_read_only_call.assert_called()

    @timeout(10, timeout_exception=StopIteration)
    def test_call_to_poll_audit_request_when_enabled_as_regular_node(self):
        """
        Tests that calling poll_audit_requests executes if a regular node calls it when
        the police node audit option is enabled.
        """
        with mock.patch('audit.audit.QSPAuditNode.is_police_officer', return_value=False), \
             mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                        return_value=0) as mk_read_only_call:
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            poll_requests_instance.config._Config__enable_police_audit_polling = True
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            # the function call is going to fail, but we only care about whether
            # this function will be called
            mk_read_only_call.assert_called()

    @timeout(10, timeout_exception=StopIteration)
    def test_poll_audit_request_deduplication_exceptions(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)

        def mocked__get_next_audit_request():
            raise DeduplicationException('mocked exception')

        poll_requests_instance._PollRequestsThread__get_next_audit_request = \
            mocked__get_next_audit_request
        # any request available is 1
        with mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                   return_value=1):
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            self.assert_event_table_contains(self.__config, [])

    @timeout(10, timeout_exception=StopIteration)
    def test_poll_audit_request_when_not_confirmed(self):
        poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)

        # myMostRecentAssignedAudit, make the block number far into the future,
        # so confirmation fails
        with mock.patch('audit.threads.poll_requests_thread.mk_read_only_call',
                   return_value=(1, 0, 0, 0, 1000)):
            self.__config.event_pool_manager.is_request_processed = MagicMock()
            poll_requests_instance._PollRequestsThread__poll_audit_request(self.__config.web3_client.eth.blockNumber)
            self.__config.event_pool_manager.is_request_processed.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_start_stop(self):
        # start the thread, signal stop and exit. use mock not to make work
        config = fetch_config(inject_contract=True)
        thread = PollRequestsThread(config, self.__block_mined_polling_thread)
        thread.start()
        while not thread.exec:
            sleep(0.1)
        thread.stop()
        self.assertFalse(thread.exec)

    def __test_police_poll_event(self, is_police, is_new_assignment, is_already_processed,
                                 should_add_evt, is_confirmed=True):
        # Configures the behaviour of is_police_officer
        with mock.patch('audit.audit.QSPAuditNode.is_police_officer', return_value=is_police):
            if is_confirmed:
                self.__config._Config__n_blocks_confirmation = 0
            else:
                self.__config._Config__n_blocks_confirmation = 1000
            poll_requests_instance = PollRequestsThread(self.__config, self.__block_mined_polling_thread)
            # Configures the behaviour of __get_next_police_assignment
            poll_requests_instance._PollRequestsThread__get_next_police_assignment = MagicMock()
            poll_requests_instance._PollRequestsThread__get_next_police_assignment.return_value = \
                [is_new_assignment, 1, 0, "some-url", 1, False]

            # Configures the behaviour of __is_request_processed
            self.__config.event_pool_manager.is_request_processed = MagicMock()
            self.__config.event_pool_manager.is_request_processed.return_value = \
                is_already_processed

            # Configures the behaviour of __add_evt_to_db
            poll_requests_instance._PollRequestsThread__add_evt_to_db = MagicMock()

            # Polls for police requests
            poll_requests_instance._PollRequestsThread__poll_police_request(self.__config.web3_client.eth.blockNumber)

            if should_add_evt:
                poll_requests_instance._PollRequestsThread__add_evt_to_db.assert_called()
            else:
                poll_requests_instance._PollRequestsThread__add_evt_to_db.assert_not_called()
