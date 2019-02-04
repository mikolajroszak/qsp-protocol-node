####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import apsw
import unittest

from unittest import mock

from config import config_value
from evt import EventPoolManager
from helpers.resource import remove
from helpers.resource import resource_uri
from helpers.qsp_test import QSPTest
from utils.io import fetch_file, load_yaml


class TestEvtPoolManager(QSPTest):
    PROCESSED = []

    db_file = None

    @classmethod
    def setUpClass(cls):
        cfg = load_yaml(fetch_file(resource_uri("test_config.yaml")))
        TestEvtPoolManager.db_file = config_value(cfg, '/dev/evt_db_path')
        remove(TestEvtPoolManager.db_file)

    def setUp(self):
        self.evt_pool_manager = EventPoolManager(TestEvtPoolManager.db_file)
        self.evt_first = {'request_id': 1,
                          'requestor': 'x',
                          'contract_uri': 'x',
                          'evt_name': 'x',
                          'block_nbr': 111,
                          'status_info': 'x',
                          'fk_type': 'AU',
                          'price': 12}
        self.evt_second = {'request_id': 17,
                           'requestor': 'x',
                           'contract_uri': 'x',
                           'evt_name': 'x',
                           'block_nbr': 555,
                           'status_info': 'x',
                           'fk_type': 'AU',
                           'price': 12}
        TestEvtPoolManager.PROCESSED = []

    def tearDown(self):
        """
        Clears the database after the test.
        """
        self.evt_pool_manager.close()
        remove(TestEvtPoolManager.db_file)
        TestEvtPoolManager.PROCESSED = []

    def test_encode(self):
        """
        Tests that encoding dictionaries to string values works.
        """
        self.assertIsNone(EventPoolManager._EventPoolManager__encode(None))
        to_encode = {"price": 1, "block_nbr": 2, "anything": "string"}
        encoded = EventPoolManager._EventPoolManager__encode(to_encode)
        self.assertEqual("1", encoded["price"])
        self.assertEqual("2", encoded["block_nbr"])
        self.assertEqual("string", encoded["anything"])

    def test_decode(self):
        """
        Tests that encoding dictionaries to string values works.
        """
        self.assertIsNone(EventPoolManager._EventPoolManager__decode(None))
        to_decode = {"price": "1", "block_nbr": "2", "anything": "string"}
        encoded = EventPoolManager._EventPoolManager__decode(to_decode)
        self.assertEqual(1, encoded["price"])
        self.assertEqual(2, encoded["block_nbr"])
        self.assertEqual("string", encoded["anything"])

    def test_get_event_by_request_id(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        evt = self.evt_pool_manager.get_event_by_request_id(self.evt_first['request_id'])
        for key in self.evt_first.keys():
            self.assertEqual(evt[key], self.evt_first[key])
        evt = self.evt_pool_manager.get_event_by_request_id(999)
        self.assertEqual({}, evt)

    def test_is_event_processed(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        processed = self.evt_pool_manager.is_request_processed(self.evt_first['request_id'])
        self.assertTrue(processed)
        processed = self.evt_pool_manager.is_request_processed(999)
        self.assertFalse(processed)

    def test_get_next_block_nbr(self):
        self.assertEqual(0, self.evt_pool_manager.get_next_block_number())
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        block_number = self.evt_pool_manager.get_next_block_number()
        self.assertEqual(self.evt_second['block_nbr'] + 1, block_number)

    def test_get_latest_block_nbr(self):
        self.assertEqual(-1, self.evt_pool_manager.get_latest_block_number())
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        block_number = self.evt_pool_manager.get_latest_block_number()
        self.assertEqual(self.evt_second['block_nbr'], block_number)

    def test_get_latest_request_id(self):
        self.assertEqual(-1, self.evt_pool_manager.get_latest_request_id())
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        request_id = self.evt_pool_manager.get_latest_request_id()
        self.assertEqual(self.evt_second['request_id'], request_id)

    def test_close(self):
        self.evt_pool_manager.close()
        self.assertFalse(self.evt_pool_manager.sql3lite_worker.thread_running)

    def test_process_incoming_events(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)

        def process(evt):
            TestEvtPoolManager.PROCESSED += [evt["request_id"]]

        self.evt_pool_manager.process_incoming_events(process)
        self.evt_pool_manager.close()
        self.assertTrue(self.evt_first["request_id"] in TestEvtPoolManager.PROCESSED)
        self.assertTrue(self.evt_second["request_id"] in TestEvtPoolManager.PROCESSED)

    def test_process_submission_events(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        self.evt_pool_manager.sql3lite_worker.execute("update audit_evt set fk_status = 'SB'")

        def process(evt, current_block):
            TestEvtPoolManager.PROCESSED += [evt["request_id"]]

        self.evt_pool_manager.process_submission_events(process, 0)
        self.evt_pool_manager.close()
        self.assertTrue(self.evt_first["request_id"] in TestEvtPoolManager.PROCESSED)
        self.assertTrue(self.evt_second["request_id"] in TestEvtPoolManager.PROCESSED)

    def test_process_events_to_be_submitted(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_second)
        self.evt_pool_manager.sql3lite_worker.execute("update audit_evt set fk_status = 'TS'")

        def process(evt):
            TestEvtPoolManager.PROCESSED += [evt["request_id"]]

        self.evt_pool_manager.process_events_to_be_submitted(process)
        self.evt_pool_manager.close()
        self.assertTrue(self.evt_first["request_id"] in TestEvtPoolManager.PROCESSED)
        self.assertTrue(self.evt_second["request_id"] in TestEvtPoolManager.PROCESSED)

    def test_set_evt_status_to_be_submitted(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_first['tx_hash'] = 'hash'
        self.evt_first['audit_uri'] = 'uri'
        self.evt_first['audit_hash'] = 'hash'
        self.evt_first['audit_state'] = 'state'
        self.evt_first['full_report'] = 'full_report'
        self.evt_first['compressed_report'] = 'compressed_report'
        self.evt_pool_manager.set_evt_status_to_be_submitted(self.evt_first)
        evt = self.evt_pool_manager.get_event_by_request_id(self.evt_first['request_id'])
        self.assertEqual(evt['fk_status'], 'TS')
        self.evt_pool_manager.close()

    def test_set_evt_status_to_submitted(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.sql3lite_worker.execute("update audit_evt set fk_status = 'TS'")
        self.evt_first['tx_hash'] = 'hash'
        self.evt_first['audit_uri'] = 'uri'
        self.evt_first['audit_hash'] = 'hash'
        self.evt_first['audit_state'] = 'state'
        self.evt_pool_manager.set_evt_status_to_submitted(self.evt_first)
        evt = self.evt_pool_manager.get_event_by_request_id(self.evt_first['request_id'])
        self.assertEqual(evt['fk_status'], 'SB')
        self.evt_pool_manager.close()

    def test_set_evt_status_to_done(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.set_evt_status_to_done(self.evt_first)
        evt = self.evt_pool_manager.get_event_by_request_id(self.evt_first['request_id'])
        self.assertEqual(evt['fk_status'], 'DN')
        self.evt_pool_manager.close()

    def test_set_evt_status_to_err(self):
        self.evt_pool_manager.add_evt_to_be_assigned(self.evt_first)
        self.evt_pool_manager.set_evt_status_to_error(self.evt_first)
        evt = self.evt_pool_manager.get_event_by_request_id(self.evt_first['request_id'])
        self.assertEqual(evt['fk_status'], 'ER')
        self.evt_pool_manager.close()

    def test_error_init(self):
        try:
            self.evt_pool_manager = EventPoolManager(None)
            self.fail("An error should have been raised")
        except TypeError:
            # expected
            pass

    def test_insert_error_handler(self):
        error = apsw.ConstraintError("audit_evt.request_id")
        wrong_error = apsw.ConstraintError()
        query = "iNserT something audit_evt.request_id"
        wrong_query = "select"
        values = ()

        class Sqlite3WorkerMock:
            def __init__(self):
                pass

        with mock.patch('evt.evt_pool_manager.logger') as logger_mock:
            worker_mock = Sqlite3WorkerMock()
            EventPoolManager.insert_error_handler(worker_mock, query, values=values, err=error)
            self.assertTrue(logger_mock.warning.called)
            self.assertFalse(logger_mock.error.called)

        with mock.patch('evt.evt_pool_manager.logger') as logger_mock:
            # Misses proper error message
            worker_mock = Sqlite3WorkerMock()
            EventPoolManager.insert_error_handler(worker_mock, query, values=values, err=wrong_error)
            self.assertFalse(logger_mock.warning.called)
            self.assertTrue(logger_mock.error.called)

        with mock.patch('evt.evt_pool_manager.logger') as logger_mock:
            # Wrong query
            worker_mock = Sqlite3WorkerMock()
            EventPoolManager.insert_error_handler(worker_mock, wrong_query, values=values, err=error)
            self.assertFalse(logger_mock.warning.called)
            self.assertTrue(logger_mock.error.called)


if __name__ == '__main__':
    unittest.main()
