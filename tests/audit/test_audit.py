"""
Tests the flow of receiving audit requests and 
their flow within the QSP audit node
"""
import os
import unittest
from timeout_decorator import timeout
from threading import Thread

from audit import QSPAuditNode
from config import Config
from helpers.resource import resource_uri


class TestQSPAuditNode(unittest.TestCase):

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__cfg = Config("test", resource_uri("test_config.yaml"))
        self.__audit_node = QSPAuditNode(
            self.__cfg
        )
        self.__request_id = 123;

        def exec():
            self.__audit_node.run()

        # Starts the execution of the QSP audit node
        Thread(target=exec, name="QSP_audit_node_thread").start()

    @timeout(15, timeout_exception=StopIteration)
    def test_contract_audit_request(self):
        """
        Tests the entire flow of an audit request, from a request
        to the production of a report back in the blockchain.
        """
        # Sets a filter for report submission events
        evt_filter = self.__cfg.internal_contract.on("LogReportSubmitted")
        evts = []

        buggy_contract = resource_uri("DAOBug.sol")

        self.__requestAudit(buggy_contract)

        # Busy waits on receiving events up to the configured
        # timeout (15s)
        while evts == []:
            evts = evt_filter.get()

        self.assertTrue(len(evts) == 1)
        self.assertEqual(evts[0]['event'], "LogReportSubmitted")
        self.assertEqual(evts[0]['args']['uri'], buggy_contract)
        self.assertEqual(evts[0]['args']['requestId'], self.__request_id)
        self.assertEqual(evts[0]['args']['auditor'], self.__cfg.account)

    def __requestAudit(self, contract_uri, price=100):
        """
        Submits a request for audit of a given target contract.
        """
        from web3 import Web3

        # Submits a request for auditing a smart contract
        self.__cfg.internal_contract.transact({"from": self.__cfg.account}).doAudit(
            self.__request_id,
            self.__cfg.account,
            contract_uri,
            price,
        )

    def tearDown(self):
        """
        Stops the execution of the current QSP audit node.
        """
        self.__audit_node.stop()


if __name__ == '__main__':
    unittest.main()
