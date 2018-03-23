"""
Tests the flow of receiving audit requests and 
their flow within the QSP audit node
"""
import contextlib
import os
import unittest
import json
import apsw
import yaml
import os
from random import randint
from timeout_decorator import timeout
from threading import Thread
from time import sleep

from audit import QSPAuditNode
from config import Config
from helpers.resource import resource_uri
from utils.io import fetch_file, digest
from utils.db import get_first

class TestQSPAuditNode(unittest.TestCase):
    __AUDIT_STATE_SUCCESS = 4
    __AUDIT_STATE_ERROR = 5

    def __clean_up_pool_db(self):
        config_file = fetch_file(self.__config_file_uri)

        with open(config_file) as yaml_file:
            config_settings = yaml.load(yaml_file)[self.__env]

        db_path = config_settings['evt_db_path']
        with contextlib.suppress(FileNotFoundError):
            os.remove(db_path)


    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__env = os.environ["ENV"] if "ENV" in os.environ else "local"
        print("CONFIG_SELECTED")
        print(self.__env)

        self.__config_file_uri = resource_uri("test_config.yaml")
        self.__clean_up_pool_db()

        self.__cfg = Config(self.__env, self.__config_file_uri)
        self.__audit_node = QSPAuditNode(
            self.__cfg
        )

        def exec():
            self.__audit_node.run()

        audit_node_thread = Thread(target=exec, name="Audit node")
        audit_node_thread.start()

    def __assert_audit_request_state(self, request_id, expected_audit_state):
        sql3lite_worker = self.__cfg.event_pool_manager.sql3lite_worker

        # Busy waits on receiving events up to the configured
        # timeout (60s)
        row = None
        while True:
            row = get_first(sql3lite_worker.execute("select * from audit_evt where fk_status = 'DN'"))
            if row != {} and row['request_id'] == request_id:
                break
            else:
                sleep(5)

        self.assertEqual(row['evt_name'], "LogAuditRequestAssigned")
        self.assertTrue(int(row['block_nbr']) > 0)
        self.assertEqual(int(row['price']), 100)
        self.assertEqual(row['submission_attempts'], 1)
        self.assertEqual(row['is_persisted'], True)

        self.assertTrue(row['tx_hash'] is not None)
        self.assertTrue(row['contract_uri'] is not None)
        
        report_uri = row['report_uri']
        print (report_uri)
        audit_state = row['audit_state']
        print (audit_state)
        report_file = fetch_file(report_uri)
        self.assertEqual(digest(report_file), row['report_hash'])
        self.assertEqual(audit_state, expected_audit_state)

    @timeout(80, timeout_exception=StopIteration)
    def test_contract_audit_request(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("DAOBug.sol")

        request_id = randint(0, 10000)
        self.__requestAudit(buggy_contract, request_id, 100)
        self.__assert_audit_request_state(request_id, self.__AUDIT_STATE_SUCCESS)

    @timeout(80, timeout_exception=StopIteration)
    def test_contract_audit_request_with_compilation_error(self):
        """
        Tests the entire flow of an erroneous audit request, from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("BasicToken.sol")

        request_id = randint(0, 10000)
        self.__requestAudit(buggy_contract, request_id, 100)
        self.__assert_audit_request_state(request_id, self.__AUDIT_STATE_ERROR)

    def __requestAudit(self, contract_uri, request_id, price):
        """
        Submits a request for audit of a given target contract.
        """
        from web3 import Web3

        # Submits a request for auditing a smart contract
        self.__cfg.internal_contract.transact({"from": self.__cfg.account}).queueAudit(
            request_id,
            self.__cfg.account,
            contract_uri,
            price,
        )

    def tearDown(self):
        """
        Stops the execution of the current QSP audit node.
        """
        self.__audit_node.stop()
        self.__clean_up_pool_db()


if __name__ == '__main__':
    unittest.main()
