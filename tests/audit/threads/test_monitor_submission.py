####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################


from time import sleep
from unittest import mock
from unittest.mock import MagicMock

from audit import MonitorSubmissionThread
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config
from timeout_decorator import timeout
from utils.eth import mk_read_only_call


class TestMonitorSubmissionThreads(QSPTest):

    def setUp(self):
        self.config = fetch_config(inject_contract=True)
        self.thread = MonitorSubmissionThread(self.config)
        self.evt_pool_manager = self.thread.config.event_pool_manager
        self.evt_pool_manager.set_evt_status_to_error = MagicMock()
        self.evt_pool_manager.set_evt_status_to_be_submitted = MagicMock()
        self.evt_pool_manager.set_evt_status_to_done = MagicMock()
        self.timeout_limit_blocks = mk_read_only_call(
            self.config, self.config.audit_contract.functions.getAuditTimeoutInBlocks()
        )

    def test_init(self):
        self.assertEqual(self.config, self.thread.config)

    @timeout(15, timeout_exception=StopIteration)
    def test_timeout_after_reaching_global_limit(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'assigned_block_nbr': current_block - self.timeout_limit_blocks,
            'submission_attempts': 1,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            event['status_info'] = "Submission of audit report outside completion window ({0} blocks)".format(
                self.timeout_limit_blocks
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_timeout_after_reaching_global_limit_but_missing_assigned_block_nbr(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_attempts': 1,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            self.assertRaises(
                KeyError,
                self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_missing_submission_attempts(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'assigned_block_nbr': current_block - self.timeout_limit_blocks,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            self.assertRaises(
                KeyError,
                self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_timeout_when_possible_to_resubmit(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'tx_hash': 'some-hash',
            'assigned_block_nbr': (current_block + 1 - self.timeout_limit_blocks),
            'submission_attempts': 1,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            event['status_info'] = "Attempting to resubmit report 17 (retry = 2)"
            event["tx_hash"] = None
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_error.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_timeout_when_possible_to_resubmit_but_missing_assigned_block_nbr(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_attempts': 1,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            self.assertRaises(
                KeyError,
                self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_timeout_after_max_resubmission_attempts(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'assigned_block_nbr': (current_block + 1 - self.timeout_limit_blocks),
            'submission_attempts': MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            event['status_info'] = "Reached maximum number of submission attempts ({0})".format(
                MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_timeout_after_max_resubmission_attempts_but_missing_assigned_block_nbr(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_attempts': MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            self.assertRaises(
                KeyError,
                self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_successfull_submission(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_block_nbr': current_block - self.config.n_blocks_confirmation,
            'submission_attempts': MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS,
            'request_id': 17
        }

        with mock.patch(
            'audit.threads.monitor_submission_thread.mk_read_only_call',
            side_effect=[self.timeout_limit_blocks, True]
        ):
            with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                            return_value=[event]):
                self.thread._MonitorSubmissionThread__process_submissions()
                event['status_info'] = "Report successfully submitted"
                self.evt_pool_manager.set_evt_status_to_done.assert_called_with(event)
                self.evt_pool_manager.set_evt_status_to_error.assert_not_called()
                self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_successfull_submission_but_missing_submission_block_nbr(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_attempts': MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS,
            'request_id': 17
        }

        with mock.patch(
            'audit.threads.monitor_submission_thread.mk_read_only_call',
            side_effect=[self.timeout_limit_blocks, True]
        ):
            with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                            return_value=[event]):
                self.thread._MonitorSubmissionThread__process_submissions()
                self.assertRaises(
                    KeyError,
                    self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
                )

    @timeout(15, timeout_exception=StopIteration)
    def test_waiting_for_submission_confirmation(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock
        self.config._Config__n_blocks_confirmation = 10

        event = {
            'submission_block_nbr': current_block - self.config.n_blocks_confirmation + 1,
            'submission_attempts': MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS,
            'request_id': 17
        }

        with mock.patch(
            'audit.threads.monitor_submission_thread.mk_read_only_call',
            side_effect=[self.timeout_limit_blocks, True]
        ):
            with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                            return_value=[event]):
                self.thread._MonitorSubmissionThread__process_submissions()
                self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()
                self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
                self.evt_pool_manager.set_evt_status_to_error.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_waiting_for_submission_confirmation_but_missing_submission_block_nbr(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock
        self.config._Config__n_blocks_confirmation = 10

        event = {
            'submission_attempts': MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS,
            'request_id': 17
        }

        with mock.patch(
            'audit.threads.monitor_submission_thread.mk_read_only_call',
            side_effect=[self.timeout_limit_blocks, True]
        ):
            with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                            return_value=[event]):
                self.thread._MonitorSubmissionThread__process_submissions()
                self.assertRaises(
                    KeyError,
                    self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
                )
                self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
                self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
                self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    @timeout(15, timeout_exception=StopIteration)
    def test_monitor_submission_timeout_called_through_start(self):
        event = {'block_nbr': -self.config.submission_timeout_limit_blocks - 5, 'request_id': 17}
        return_value = [event]
        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=return_value):
            self.thread.start()
            while not self.evt_pool_manager.set_evt_status_to_error.called:
                sleep(0.1)

        if self.thread.exec:
            self.thread.stop()

    @timeout(15, timeout_exception=StopIteration)
    def test_generic_exception(self):
        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_block_nbr': current_block - self.config.n_blocks_confirmation,
            'request_id': 17
        }

        with mock.patch(
            'audit.threads.monitor_submission_thread.mk_read_only_call',
            side_effect=[True, Exception("generic")]
        ):
            with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                            return_value=[event]):
                self.thread._MonitorSubmissionThread__process_submissions()
                self.assertRaises(
                    Exception,
                    self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
                )
                self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
                self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
                self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

        current_block = 100000000000

        web3_mock = MagicMock()
        web3_mock.eth.blockNumber = current_block
        self.config._Config__web3_client = web3_mock

        event = {
            'submission_attempts': 1,
            'request_id': 17
        }

        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=[event]):
            self.thread._MonitorSubmissionThread__process_submissions()
            self.assertRaises(
                KeyError,
                self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
            )
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)
            self.evt_pool_manager.set_evt_status_to_done.assert_not_called()
            self.evt_pool_manager.set_evt_status_to_be_submitted.assert_not_called()

    # TODO
    # This is currently broken - starting a thread does not change its
    # __exec automatically. To be fixed separately. See QSP-1073
    #
    # @timeout(15, timeout_exception=StopIteration)
    # def test_start_stop(self):
    #     # start the thread, signal stop and exit, use mock not to make work
    #     with mock.patch('audit.threads.monitor_submission_thread.MonitorSubmissionThread'
    #                     '._MonitorSubmissionThread__monitor_submission_timeout'):
    #         handle = self.thread.start()
    #         self.assertTrue(self.thread.exec)
    #         self.thread.stop()
    #         self.assertFalse(self.thread.exec)
    #         handle.join()
