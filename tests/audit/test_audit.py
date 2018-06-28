"""
Tests the flow of receiving audit requests and
their flow within the QSP audit node
"""
import contextlib
import os
import subprocess
import tempfile
import unittest
import yaml

from timeout_decorator import timeout
from threading import Thread
from time import sleep

from audit import QSPAuditNode
from config import Config
from helpers.resource import (
    resource_uri,
    project_root,
)
from pathlib import Path
from utils.io import fetch_file, digest_file
from utils.db import get_first


class TestQSPAuditNode(unittest.TestCase):
    __AUDIT_STATE_SUCCESS = 4
    __AUDIT_STATE_ERROR = 5
    __REQUEST_ID = 1
    __PRICE = 100

    @classmethod
    def __clean_up_pool_db(cls, evt_db_path):
        print("Cleaning test database")
        with contextlib.suppress(FileNotFoundError):
            os.remove(evt_db_path)

    @classmethod
    def fetch_config(cls):
        config_file_uri = resource_uri("test_config.yaml")
        return Config("local", config_file_uri)

    @classmethod
    def setUpClass(cls):
        config = TestQSPAuditNode.fetch_config()
        TestQSPAuditNode.__clean_up_pool_db(config.evt_db_path)

        all_wrappers_dir = Path("{0}/analyzers/wrappers".format(project_root()))

        i = 0
        # Iterate over all the wrappers within the analyzers folder
        for entry in all_wrappers_dir.iterdir():
            if not entry.is_dir():
                continue

            wrapper_home = entry

            env = dict(os.environ)
            env['WRAPPER_HOME'] = wrapper_home

            storage_dir = config.analyzers[i].wrapper.storage_dir
            env['STORAGE_DIR'] = storage_dir

            # Creates storage directory if it does not exits
            if not os.path.exists(storage_dir):
                os.makedirs(storage_dir)

            once_process = subprocess.run(
                "{0}/once".format(wrapper_home),
                shell=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )

            if once_process.returncode == 1:
                # An error occurred
                raise Exception("Error invoking once (return value is not 0). Output is {0}".format(once_process.stdout))

            i += 1

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__config = TestQSPAuditNode.fetch_config()
        self.__audit_node = QSPAuditNode(self.__config)

        self.__getNextAuditRequest_filter = self.__config.audit_contract.events.getNextAuditRequest_called.createFilter(
            fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
        )
        self.__submitReport_filter = self.__config.audit_contract.events.submitReport_called.createFilter(
            fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
        )
        self.__setAnyRequestAvailableResult_filter = self.__config.audit_contract.events.setAnyRequestAvailableResult_called.createFilter(
            fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
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
        TestQSPAuditNode.__clean_up_pool_db(self.__config.evt_db_path)

    def __assert_audit_request_state(self, request_id, expected_audit_state):
        sql3lite_worker = self.__config.event_pool_manager.sql3lite_worker

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

        audit_uri = row['audit_uri']
        audit_state = row['audit_state']
        audit_file = fetch_file(audit_uri)

        self.assertEqual(digest_file(audit_file), row['audit_hash'])
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
        # since we're mocking the smart contract, we should explicitly call its internals
        buggy_contract = resource_uri("DAOBug.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__requestAudit(buggy_contract, self.__PRICE)
        )

        self.evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__config.audit_contract.functions.emitLogAuditFinished(
                self.__REQUEST_ID,
                self.__config.account,
                0,
                "",
                "",
                0).transact({"from": self.__config.account})
        )
        self.__assert_audit_request_state(self.__REQUEST_ID, self.__AUDIT_STATE_SUCCESS)

    @timeout(80, timeout_exception=StopIteration)
    def test_buggy_contract_audit_request(self):
        """
        Tests the entire flow of an erroneous audit request, from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("BasicToken.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__requestAudit(buggy_contract, self.__PRICE)
        )

        self.evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__config.audit_contract.functions.emitLogAuditFinished(self.__REQUEST_ID,
                                                                     self.__config.account,
                                                                     0,
                                                                     "",
                                                                     "",
                                                                     0).transact({"from": self.__config.account})
        )

        self.__assert_audit_request_state(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR)

    @timeout(80, timeout_exception=StopIteration)
    def test_target_contract_in_non_raw_text_file(self):
        """
        Tests the entire flow of an audit request of a non-raw text file contract (e.g., HTML), from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("DappBinWallet.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__requestAudit(buggy_contract, self.__PRICE)
        )

        self.evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__config.audit_contract.functions.emitLogAuditFinished(self.__REQUEST_ID,
                                                                     self.__config.account,
                                                                     0,
                                                                     "",
                                                                     "",
                                                                     0).transact({"from": self.__config.account})
        )

        self.__assert_audit_request_state(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR)

    def __requestAudit(self, contract_uri, price):
        """
        Emulates requesting for a new audit.
        """
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__config.audit_contract.functions.setAnyRequestAvailableResult(1).transact(
                {"from": self.__config.account})
        )
        self.evt_wait_loop(self.__setAnyRequestAvailableResult_filter)

        self.evt_wait_loop(self.__getNextAuditRequest_filter)

        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__config.audit_contract.functions.setAnyRequestAvailableResult(0).transact(
                {"from": self.__config.account})
        )
        self.evt_wait_loop(self.__setAnyRequestAvailableResult_filter)

        request_id = 1
        requester = self.__config.account
        auditor = self.__config.account
        transaction_fee = 123
        timestamp = 40

        # Emulates assigning a request for a given target contract by submitting the appropriate event.
        return self.__config.audit_contract.functions.emitLogAuditAssigned(
            request_id,
            requester,
            auditor,
            contract_uri,
            price,
            transaction_fee,
            timestamp).transact({"from": self.__config.account})


if __name__ == '__main__':
    unittest.main()
