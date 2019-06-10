####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from audit import ComputeGasPriceThread
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config
from timeout_decorator import timeout

from time import sleep


class TestComputeGasPriceThread(QSPTest):
    __CONFIG = None

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        cls.__CONFIG = fetch_config(inject_contract=False,
                                    filename="test_config_with_no_analyzers.yaml")

    def test_init(self):
        thread = ComputeGasPriceThread(TestComputeGasPriceThread.__CONFIG)
        self.assertEqual(TestComputeGasPriceThread.__CONFIG, thread.config)

    @timeout(30, timeout_exception=StopIteration)
    def test_gas_price_computation_static(self):
        config = fetch_config(inject_contract=False, filename="test_config_with_no_analyzers.yaml")
        config._Config__default_gas_price_wei = 12345
        config._Config__gas_price_strategy = "static"
        thread = ComputeGasPriceThread(config)
        thread.compute_gas_price()
        self.assertEqual(config.gas_price_wei, 12345)

    @timeout(30, timeout_exception=StopIteration)
    def test_gas_price_computation_empty_blockchain(self):
        thread = ComputeGasPriceThread(TestComputeGasPriceThread.__CONFIG)
        # tests for errors when there are too few blocks in the blockchain history
        try:
            thread.compute_gas_price()
            self.assertTrue(TestComputeGasPriceThread.__CONFIG.gas_price_wei > 0)
        except Exception:
            self.fail("Computing gas price on an empty blockchain failed.")

    @timeout(15, timeout_exception=StopIteration)
    def test_start_stop(self):
        thread = ComputeGasPriceThread(TestComputeGasPriceThread.__CONFIG)
        thread.start()
        while not thread.exec:
            sleep(0.1)
        thread.stop()
        self.assertFalse(thread.exec)
