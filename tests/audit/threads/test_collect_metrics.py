####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from time import sleep
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
            thread.start()
            while not thread.exec:
                sleep(0.1)
            thread.stop()
            self.assertFalse(thread.exec)
