"""
Tests the flow of receiving audit requests and 
their flow within the QSP audit node
"""
import contextlib
import os
import unittest
import json
import sqlite3
import yaml
import os
from random import randint
from timeout_decorator import timeout
from threading import Thread

from audit import QSPAuditNode
from config import Config
from helpers.resource import resource_uri
from utils.io import fetch_file, digest

class TestQSPAuditNode(unittest.TestCase):

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
        self.__env = "test"
        self.__config_file_uri = resource_uri("test_config.yaml")

        self.__clean_up_pool_db()

        self.__cfg = Config(self.__env, self.__config_file_uri)
        self.__audit_node = QSPAuditNode(
            self.__cfg
        )

        def exec():
            self.__audit_node.run()

        # Starts the execution of the QSP audit node
        Thread(target=exec, name="QSP_audit_node_thread").start()

    @timeout(30, timeout_exception=StopIteration)
    def test_contract_audit_request(self):
        """
        Tests the entire flow of an audit request, from a request
        to the production of a report back in the blockchain.
        """
        # Sets a filter for report submission events
        evt_filter = self.__cfg.internal_contract.on("LogReportSubmitted")
        evts = []

        buggy_contract = resource_uri("DAOBug.sol")

        request_id = randint(0, 1000)
        self.__requestAudit(buggy_contract, request_id)

        # Busy waits on receiving events up to the configured
        # timeout (30s)
        while evts == []:
            evts = evt_filter.get()

        self.assertTrue(len(evts) == 1)
        self.assertEqual(evts[0]['event'], "LogReportSubmitted")
        self.assertEqual(evts[0]['args']['uri'], buggy_contract)
        self.assertEqual(evts[0]['args']['requestId'], request_id)
        self.assertEqual(evts[0]['args']['auditor'], self.__cfg.account)
        
        report = json.loads(evts[0]['args']['report']);
        print (report['report_uri'])
        report_file = fetch_file(report['report_uri'])
        self.assertEqual(digest(report_file), report['report_sha256']);

        report = json.loads(evts[0]['args']['report'])
        print (report['report_uri'])
        report_file = fetch_file(report['report_uri'])
        self.assertEqual(digest(report_file), report['report_sha256'])

    def __requestAudit(self, contract_uri, request_id, price=100):
        """
        Submits a request for audit of a given target contract.
        """
        from web3 import Web3

        # Submits a request for auditing a smart contract
        self.__cfg.internal_contract.transact({"from": self.__cfg.account}).doAudit(
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
