####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from time import sleep
from unittest import mock
from unittest.mock import MagicMock

from audit import MonitorSubmissionThread
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config
from timeout_decorator import timeout


class TestMonitorSubmissionThreads(QSPTest):

    def setUp(self):
        self.config = fetch_config(inject_contract=True)
        self.thread = MonitorSubmissionThread(self.config)
        self.evt_pool_manager = self.thread.config.event_pool_manager
        self.evt_pool_manager.set_evt_status_to_error = MagicMock()

    def test_init(self):
        self.assertEqual(self.config, self.thread.config)

    def test_monitor_submission_timeout_called_proxy(self):

        event = {'block_nbr': -self.config.submission_timeout_limit_blocks - 5, 'request_id': 17}
        return_value = [event]
        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=return_value):
            self.thread._MonitorSubmissionThread__process_submissions()
            event['status_info'] = 'Submission timeout'
            self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)

    def test_monitor_submission_timeout_not_called_proxy(self):
        event = {'block_nbr': self.config.submission_timeout_limit_blocks - 5, 'request_id': 17}
        return_value = [event]
        with mock.patch('evt.evt_pool_manager.EventPoolManager._EventPoolManager__exec_sql',
                        return_value=return_value):
            self.thread._MonitorSubmissionThread__process_submissions()
            event['status_info'] = 'Submission timeout'
            self.evt_pool_manager.set_evt_status_to_error.assert_not_called()

    def test_monitor_submission_timeout_called(self):
        current_block = 100000000000
        last_valid = current_block - self.config.submission_timeout_limit_blocks
        event = {'block_nbr': last_valid - 1, 'request_id': 17}
        self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
        self.evt_pool_manager.set_evt_status_to_error.assert_called_with(event)

    def test_monitor_submission_timeout_not_called(self):
        current_block = 100000000000
        last_valid = current_block - self.config.submission_timeout_limit_blocks
        event = {'block_nbr': last_valid, 'request_id': 17}
        self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)
        self.evt_pool_manager.set_evt_status_to_error.assert_not_called()

    def test_monitor_submission_timeout_key_error_no_fail(self):
        current_block = 100000000000
        last_valid = current_block - self.config.submission_timeout_limit_blocks
        event = {'block_nbr': last_valid, 'request_id': 17}
        self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)

    def test_monitor_submission_timeout_exception_no_fail(self):
        current_block = 100000000000
        last_valid = current_block - self.config.submission_timeout_limit_blocks
        event = {'block_nbr': last_valid, 'request_id': 17}
        self.thread._MonitorSubmissionThread__monitor_submission_timeout(event, current_block)

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
    def test_start_stop(self):
        # start the thread, signal stop and exit, use mock not to make work
        with mock.patch('audit.threads.monitor_submission_thread.MonitorSubmissionThread'
                        '._MonitorSubmissionThread__monitor_submission_timeout'):
            self.thread.start()
            while not self.thread.exec:
                sleep(0.1)
            self.thread.stop()
            self.assertFalse(self.thread.exec)
