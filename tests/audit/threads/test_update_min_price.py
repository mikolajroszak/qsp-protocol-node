####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from unittest import mock

from audit import UpdateMinPrice
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config
from time import sleep
from timeout_decorator import timeout
from utils.eth.tx import TransactionNotConfirmedException
from utils.eth.tx import DeduplicationException
from web3.utils.threads import Timeout


class TestUpdateMinPrice(QSPTest):
    __SLEEP_INTERVAL = 1

    def __evt_wait_loop(self, current_filter):
        events = current_filter.get_new_entries()
        while not bool(events):
            sleep(TestUpdateMinPrice.__SLEEP_INTERVAL)
            events = current_filter.get_new_entries()
        return events

    def test_init(self):
        config = fetch_config()
        thread = UpdateMinPrice(config)
        self.assertEqual(config, thread.config)

    def test_update_min_price_success(self):
        config = fetch_config()
        thread = UpdateMinPrice(config)
        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        return_value="hash"):
            thread._UpdateMinPrice__update_min_price()

    def test_update_min_price_exceptions(self):
        config = fetch_config()
        thread = UpdateMinPrice(config)
        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        side_effect=Exception):
            try:
                thread._UpdateMinPrice__update_min_price()
                self.fail("Exception was not propagated")
            except Exception:
                # expected
                pass

        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        side_effect=TransactionNotConfirmedException):
            try:
                thread._UpdateMinPrice__update_min_price()
                self.fail("Exception was not propagated")
            except TransactionNotConfirmedException:
                # expected
                pass

        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        side_effect=Timeout):
            try:
                thread._UpdateMinPrice__update_min_price()
                self.fail("Exception was not propagated")
            except Timeout:
                # expected
                pass

        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        side_effect=DeduplicationException):
            try:
                thread._UpdateMinPrice__update_min_price()
                self.fail("Exception was not propagated")
            except DeduplicationException:
                # expected
                pass

    def test_check_and_update_min_price(self):
        config = fetch_config()
        thread = UpdateMinPrice(config)
        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        return_value="hash"), \
             mock.patch('audit.threads.update_min_price.mk_read_only_call',
                        return_value=config.min_price_in_qsp + 5):
            thread.check_and_update_min_price()

    def test_stop(self):
        config = fetch_config()
        thread = UpdateMinPrice(config)
        thread.stop()
        self.assertFalse(thread.exec)

    @timeout(30, timeout_exception=StopIteration)
    def test_change_min_price(self):
        """
        Tests that the node updates the min_price on the blockchain if the config value changes
        """

        config = fetch_config()
        set_audit_price_filter = config.audit_contract.events.setAuditNodePrice_called.createFilter(
            fromBlock=max(0, config.event_pool_manager.get_latest_block_number())
        )

        # this make a one-off call
        config._Config__min_price_in_qsp = 1
        thread = UpdateMinPrice(config)
        thread._UpdateMinPrice__update_min_price()

        success = False
        while not success:
            events = self.__evt_wait_loop(set_audit_price_filter)
            for event in events:
                self.assertEqual(event['event'], 'setAuditNodePrice_called')
                if event['args']['price'] == 10 ** 18:
                    success = True
                    break
            if not success:
                sleep(TestUpdateMinPrice.__SLEEP_INTERVAL)

    @timeout(15, timeout_exception=StopIteration)
    def test_start_stop(self):
        # start the thread, signal stop and exit. use mock not to make work
        config = fetch_config()
        thread = UpdateMinPrice(config)
        with mock.patch('audit.threads.update_min_price.send_signed_transaction',
                        return_value="hash"):
            handle = thread.start()
            self.assertTrue(thread.exec)
            thread.stop()
            self.assertFalse(thread.exec)
            handle.join()
