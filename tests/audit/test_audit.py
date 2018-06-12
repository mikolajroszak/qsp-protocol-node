"""
Tests the flow of receiving audit requests and 
their flow within the QSP audit node
"""
import contextlib
import unittest
import yaml
import os
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
    __REQUEST_ID = 1
    __PRICE = 100

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

        # Steps required to perform the tests in AWS
        self.__env = os.environ["ENV"] if "ENV" in os.environ else "local"
        print("CONFIG_SELECTED")
        print(self.__env)

        self.__config_file_uri = resource_uri("test_config.yaml")
        self.__clean_up_pool_db()
        self.__cfg = Config(self.__env, self.__config_file_uri)
        self.__audit_node = QSPAuditNode(
            self.__cfg
        )
        self.__requestAudit_filter = self.__cfg.audit_contract.events.requestAudit_called.createFilter(
          fromBlock=max(0, self.__cfg.event_pool_manager.get_latest_block_number())
        )
        self.__getNextAuditRequest_filter = self.__cfg.audit_contract.events.getNextAuditRequest_called.createFilter(
            fromBlock=max(0, self.__cfg.event_pool_manager.get_latest_block_number())
        )
        self.__submitReport_filter = self.__cfg.audit_contract.events.submitReport_called.createFilter(
            fromBlock=max(0, self.__cfg.event_pool_manager.get_latest_block_number())
        )

        def exec():
            self.__audit_node.run()

        audit_node_thread = Thread(target=exec, name="Audit node")
        audit_node_thread.start()

    def tearDown(self):
        """
        Stops the execution of the current QSP audit node.
        """
        self.__audit_node.stop()
        self.__clean_up_pool_db()

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
        self.assertEqual(row['evt_name'], "LogAuditAssigned")
        self.assertTrue(int(row['block_nbr']) > 0)
        self.assertEqual(int(row['price']), 100)
        self.assertEqual(row['submission_attempts'], 1)
        self.assertEqual(row['is_persisted'], True)

        self.assertTrue(row['tx_hash'] is not None)
        self.assertTrue(row['contract_uri'] is not None)
        
        report_uri = row['report_uri']
        audit_state = row['audit_state']
        report_file = fetch_file(report_uri)
        self.assertEqual(digest(report_file), row['report_hash'])
        self.assertEqual(audit_state, expected_audit_state)

    def evt_wait_loop(self, current_filter):
        wait = True
        while wait:
            events = current_filter.get_new_entries()
            for evt in events:
                wait = False
                break
            sleep(1)


    @timeout(80, timeout_exception=StopIteration)
    def test_contract_audit_request(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("DAOBug.sol")
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__requestAudit(buggy_contract, self.__PRICE)
        )
        # since we're mocking function calls, we should wait for getNextAuditRequest to be called
        self.evt_wait_loop(self.__getNextAuditRequest_filter)
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__cfg.audit_contract.functions.emitLogAuditAssigned(self.__REQUEST_ID, self.__cfg.account).transact({"from": self.__cfg.account})
        )
        self.evt_wait_loop(self.__submitReport_filter)
        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__cfg.audit_contract.functions.emitLogAuditFinished(self.__REQUEST_ID, self.__cfg.account, 0, "", "", 0).transact({"from": self.__cfg.account})
        )
        self.__assert_audit_request_state(self.__REQUEST_ID, self.__AUDIT_STATE_SUCCESS)

    @timeout(80, timeout_exception=StopIteration)
    def test_buggy_contract_audit_request(self):
        """
        Tests the entire flow of an erroneous audit request, from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("BasicToken.sol")
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
          self.__requestAudit(buggy_contract, self.__PRICE)
        )
        self.evt_wait_loop(self.__getNextAuditRequest_filter)
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__cfg.audit_contract.functions.emitLogAuditAssigned(self.__REQUEST_ID, self.__cfg.account).transact(
                {"from": self.__cfg.account}
            )
        )
        self.evt_wait_loop(self.__submitReport_filter)
        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__cfg.audit_contract.functions.emitLogAuditFinished(self.__REQUEST_ID,
                                                                     self.__cfg.account,
                                                                     0,
                                                                     "",
                                                                     "",
                                                                     0).transact({"from": self.__cfg.account})
        )

        self.__assert_audit_request_state(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR)

    @timeout(80, timeout_exception=StopIteration)
    def test_target_contract_in_non_raw_text_file(self):
        """
        Tests the entire flow of an audit request of a non-raw text file contract (e.g., HTML), from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("DappBinWallet.sol")

        self.__cfg.web3_client.eth.waitForTransactionReceipt(
          self.__requestAudit(buggy_contract, self.__PRICE)
        )
        self.evt_wait_loop(self.__getNextAuditRequest_filter)

        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__cfg.audit_contract.functions.emitLogAuditAssigned(self.__REQUEST_ID, self.__cfg.account).transact(
                {"from": self.__cfg.account}
            )
        )
        self.evt_wait_loop(self.__submitReport_filter)
        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__cfg.web3_client.eth.waitForTransactionReceipt(
            self.__cfg.audit_contract.functions.emitLogAuditFinished(self.__REQUEST_ID,
                                                                     self.__cfg.account,
                                                                     0,
                                                                     "",
                                                                     "",
                                                                     0).transact({"from": self.__cfg.account})
        )

        self.__assert_audit_request_state(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR)

    def __requestAudit(self, contract_uri, price):
        """
        Submits a request for audit of a given target contract.
        """
        request_id = 1
        requestor = self.__cfg.account
        transaction_fee = 123
        timestamp = 40
        # don't need to actually call requestAudit. All node behaviour is in terms of events
        return self.__cfg.audit_contract.functions.emitLogAuditRequested(
            request_id,
            requestor,
            contract_uri,
            price,
            transaction_fee,
            timestamp
        ).transact({"from": self.__cfg.account})

if __name__ == '__main__':
    unittest.main()
