"""
Tests our assumptions about the database client and SQLite3 engine.
"""
import unittest
import yaml
import apsw

from config import config_value
from helpers.resource import resource_uri
from timeout_decorator import timeout
from utils.db import Sqlite3Worker
from utils.io import fetch_file


class LoggerMock:

    def __init__(self):
        self.logged = False
        self.err = None

    def error(self, msg, query, values, err):
        self.err = err
        self.logged = True
        print(msg)
        print(query)
        print(values)
        print(err)
        if isinstance(err, apsw.BusyError):
            print("NOTE: If the error appears to be 'BusyError', your test failed mid-execution. "
                  "You might need to delete the test database file defined in test_config.yaml "
                  "(currently set to /tmp/evts.test) in order to resume test execution.")


class TestSqlLite3Worker(unittest.TestCase):
    """
    Tests the functionality of the SQLite worker.
    """

    def setUp(self):
        """
        Sets up fresh database for each test.
        """
        cfg = TestSqlLite3Worker.read_yaml_setup('test_config.yaml')
        file = config_value(cfg, '/local/evt_db_path')
        self.logger_mock = LoggerMock()
        self.worker = Sqlite3Worker(self.logger_mock, file)
        self.worker.execute_script(fetch_file(resource_uri('dropdb.sql')))
        self.worker.execute_script(fetch_file(resource_uri('evt/createdb.sql', is_main=True)))

    def tearDown(self):
        """
        Clears the database after the test.
        """
        self.worker.execute_script(fetch_file(resource_uri('dropdb.sql')))
        self.worker.close()

    @timeout(3, timeout_exception=StopIteration)
    def test_execute_create_script(self):
        """
        Tests that the worker is capable of creating the database and insert items by executing a
        script.
        """
        self.assertFalse(self.logger_mock.logged)
        result = self.worker.execute("select * from evt_status")
        self.assertEqual(len(result), 6,
                         'We are expecting 5 event type records. There are {0}'.format(len(result)))
        self.assertFalse(self.logger_mock.logged)

    @timeout(3, timeout_exception=StopIteration)
    def test_inserting_duplicates_primary_key(self):
        """
        Tests that the worker does not propagate raised exception when two records with the same
        primary key are inserted in the database. Also tests that if such an insert is invoked, the
        existing values remain the same.
        """
        self.assertFalse(self.logger_mock.logged)
        result = self.worker.execute("select * from evt_status")
        # The result is string if the database is locked (caused by previously failed tests)
        self.assertFalse(isinstance(result, str))
        self.assertFalse(self.logger_mock.logged)
        original_value = [x for x in result if x['id'] == 'RQ'][0]
        # Inserts a repeated primary key
        self.worker.execute("insert into evt_status values ('RQ', 'Updated received')")
        result = self.worker.execute("select * from evt_status")
        # The result is string if the database is locked (caused by previously failed tests)
        self.assertFalse(isinstance(result, str))
        self.assertEqual(len(result), 6,
                         'We are expecting 5 event type records. There are {0}'.format(len(result)))
        new_value = [x for x in result if x['id'] == 'RQ'][0]
        self.assertEqual(new_value, original_value,
                         "The original value changed after the insert")
        # This should stay at the very end after the worker thread has been merged
        self.worker.close()
        self.assertTrue(isinstance(self.logger_mock.err, apsw.ConstraintError))
        self.assertTrue(self.logger_mock.logged)

    @timeout(3, timeout_exception=StopIteration)
    def test_wrong_select(self):
        """
        Tests that wrong select returns string and logs an error.
        """
        self.assertFalse(self.logger_mock.logged)
        result = self.worker.execute("select * from nonexistent_table")
        # The result is string if the database is locked (caused by previously failed tests)
        self.assertTrue(isinstance(result, str))
        # This should stay at the very end after the worker thread has been merged
        self.worker.close()
        self.assertTrue(self.logger_mock.logged)

    @staticmethod
    def read_yaml_setup(config_path):
        test_config = fetch_file(resource_uri(config_path))
        with open(test_config) as yaml_file:
            cfg = yaml.load(yaml_file)

        return cfg


if __name__ == '__main__':
    unittest.main()
