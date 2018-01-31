"""
Tests the flow of receiving audit requests and 
their flow within the QSP audit node
"""
import os
from timeout_decorator import timeout
from threading import Thread
import unittest

from audit import QSPAuditNode
from config import Config
from helpers.resource import resource_uri

class TestQSPAuditNode(unittest.TestCase):
    
    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__cfg = Config("test", resource_uri("test_config.yaml"))
        self.__account = self.__cfg.web3_client.eth.accounts[self.__cfg.account_id]
        self.__audit_node = QSPAuditNode(
            self.__account,
            self.__cfg.internal_contract, 
            self.__cfg.analyzer,
            self.__cfg.min_price,
            self.__cfg.evt_polling,
            self.__cfg.analyzer_output,
        )

        def exec():
            print("===> RUNNING EXEC")
            self.__audit_node.run()

        # Starts the execution of the QSP audit node
        Thread(target=exec, name="QSP_audit_node_thread").start()

    
    def test_contract_audit_request(self):
        # Sets a filter for report submission events
        evt_filter = self.__cfg.internal_contract.on("LogReportSubmitted")
        evts = []

        buggy_contract = resource_uri("DAOBug.sol")
        print("===> BUGGY CONTRACT IS " + buggy_contract)

        self.__requestAudit(buggy_contract)
        print("===> REQUEST SENT")

        # Busy waits on receiving events up to the configured
        # timeout (10s)
        while evts == []:
           evts = evt_filter.get()

        print("===> GOT SUBMISSION AS EVENT => " + str(evts))
        self.assertTrue(len(evts) == 1)


    def __requestAudit(self, contract_name):

        print("===> INSIDE __requestAudit")
        print("===> internal_contract is " + repr(self.__cfg.internal_contract))

        from web3 import Web3
        # Submits a request for auditing a smart contract
        self.__cfg.internal_contract.transact({"from": self.__account}).doAudit(
            self.__account,
            contract_name,
            100,    
        )

    def tearDown(self):
        """
        Stops the execution of the current QSP audit node.
        """
        self.__audit_node.stop()

