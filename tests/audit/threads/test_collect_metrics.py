####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from unittest import mock

from audit import CollectMetricsThread
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config
from timeout_decorator import timeout


class TestCollectMetricsThread(QSPTest):

    def test_init(self):
        config = fetch_config(inject_contract=True)
        thread = CollectMetricsThread(config)
        self.assertEqual(config, thread.config)

    def test_stop(self):
        config = fetch_config(inject_contract=True)
        thread = CollectMetricsThread(config)
        thread.stop()
        self.assertFalse(thread.exec)

    @timeout(15, timeout_exception=StopIteration)
    def test_start_stop(self):
        # start the thread, signal stop and exit. use mock not to make work
        config = fetch_config(inject_contract=True)
        thread = CollectMetricsThread(config)
        with mock.patch('audit.threads.collect_metrics_thread.MetricCollector.collect_and_send',
                        return_value=True):
            handle = thread.start()
            self.assertTrue(thread.exec)
            thread.stop()
            self.assertFalse(thread.exec)
            handle.join()
