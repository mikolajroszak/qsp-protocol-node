####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Tests the flow of receiving audit requests and their flow within the QSP audit node
"""
import unittest
from unittest import mock

from audit import QSPAuditNode
from audit import Analyzer, Wrapper
from audit.report_processing import ReportEncoder
from config import ConfigUtils, ConfigurationException
from helpers.qsp_test import QSPTest
from helpers.resource import (
    fetch_config,
    project_root,
    remove,
    resource_uri
)
from helpers.transact import safe_transact
from upload import DummyProvider

from utils.io import fetch_file, digest_file, load_json
from utils.db import get_first

from random import random
from time import sleep
from time import time
from timeout_decorator import timeout
from threading import Thread


class TestQSPAuditNode(QSPTest):
    __AUDIT_STATE_SUCCESS = 4
    __AUDIT_STATE_ERROR = 5
    __AVAILABLE_AUDIT_STATE_READY = 1
    __AVAILABLE_AUDIT_STATE_ERROR = 0
    __REQUEST_ID = 1
    __PRICE = 100
    __SLEEP_INTERVAL = 0.01

    ##############################################
    # Setup-like methods
    ##############################################

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config(inject_contract=True)
        remove(config.evt_db_path)

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__config = fetch_config(inject_contract=True)
        self.__audit_node = QSPAuditNode(self.__config)
        self.__audit_node.config._Config__upload_provider = DummyProvider()
        self.__mk_unique_storage_dir()

        # Forces analyzer wrapper to always execute their `once` script prior
        # to executing `run`
        for analyzer in self.__config.analyzers:
            remove(analyzer.wrapper.storage_dir + '/.once')

        self.__getNextAuditRequest_filter = \
            self.__config.audit_contract.events.getNextAuditRequest_called.createFilter(
                fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
            )
        self.__submitReport_filter = \
            self.__config.audit_contract.events.submitReport_called.createFilter(
                fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
            )
        self.__setAnyRequestAvailableResult_filter = \
            self.__config.audit_contract.events.setAnyRequestAvailableResult_called.createFilter(
                fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
            )
        self.__setAuditNodePrice_filter = \
            self.__config.audit_contract.events.setAuditNodePrice_called.createFilter(
                fromBlock=max(0, self.__config.event_pool_manager.get_latest_block_number())
            )

        def exec():
            self.__audit_node.run()

        audit_node_thread = Thread(target=exec, name="Audit node")
        audit_node_thread.start()

        max_initialization_seconds = 5
        num_checks = 0
        while not self.__audit_node.is_initialized:
            sleep(TestQSPAuditNode.__SLEEP_INTERVAL)
            num_checks += 100
            if num_checks == max_initialization_seconds:
                self.__audit_node.stop()
                raise Exception("Node threads could not be initialized")

    def tearDown(self):
        """
        Stops the execution of the current QSP audit node.
        """
        self.__audit_node.stop()
        remove(self.__config.evt_db_path)

    ##############################################
    # Tests
    ##############################################

    def test_not_enough_stake(self):
        self.__audit_node.stop()
        stake = 10
        required = 20
        with mock.patch('audit.audit.mk_read_only_call', side_effect=[False, required, stake]):
            try:
                self.__audit_node.run()
                self.fail("An exception was expected")
            except Exception as e:
                # expected
                expected_msg = "Audit node does {0} not have enough stake. Please stake at least " \
                               "{1} QSP into the account {2}. Current stake is {3} QSP. Please " \
                               "restart the node.".format(
                    self.__audit_node.config.account,
                    required / (10 ** 18),
                    self.__audit_node.config.audit_contract_address,
                    stake / (10 ** 18))
                self.assertEqual(expected_msg, str(e))

    @timeout(8, timeout_exception=StopIteration)
    def test_timeout_stale_events(self):
        class Web3Mock:
            def __init__(self, eth):
                self.eth = eth

        class EthMock:
            def __init__(self):
                self.blockNumber = 100
                # gas price is needed for the thread that makes computations it in the background
                # but it is irrelevant for the purposes of this test
                self.gasPrice = 10

        class ManagerMock:
            def close(self):
                pass

        # The following stops the entire audit node except for the event pool manager that needs to
        # remain open in order to handle database connection and database requests. The manager is
        # temporarily replaced by a mock object so that the close method of the audit node can stop
        # and merge all the threads, and then placed back. The manager is closed properly at the end
        # of the test before verifying the results.
        manager = self.__audit_node.config.event_pool_manager
        self.__audit_node.config._Config__event_pool_manager = ManagerMock()
        self.__audit_node.stop()
        self.__audit_node.config._Config__event_pool_manager = manager

        self.__audit_node.config._Config__web3_client = Web3Mock(EthMock())
        self.__audit_node.config._Config__submission_timeout_limit_blocks = 10
        self.__audit_node.config._Config__block_discard_on_restart = 2
        # certainly times out
        evt_first = {'request_id': 1,
                     'requestor': 'x',
                     'contract_uri': 'x',
                     'evt_name': 'x',
                     'block_nbr': 10,
                     'status_info': 'x',
                     'fk_type': 'AU',
                     'price': 12}
        # last block to time out
        evt_second = {'request_id': 17,
                      'requestor': 'x',
                      'contract_uri': 'x',
                      'evt_name': 'x',
                      'block_nbr': 90 + 2,
                      'status_info': 'x',
                      'fk_type': 'AU',
                      'price': 12}
        # first block not to time out
        evt_third = {'request_id': 18,
                     'requestor': 'x',
                     'contract_uri': 'x',
                     'evt_name': 'x',
                     'block_nbr': 91 + 2,
                     'status_info': 'x',
                     'fk_type': 'AU',
                     'price': 12}
        self.__audit_node.config.event_pool_manager.add_evt_to_be_assigned(evt_first)
        self.__audit_node.config.event_pool_manager.add_evt_to_be_assigned(
            evt_second
        )
        self.__audit_node.config.event_pool_manager.add_evt_to_be_assigned(evt_third)
        self.__audit_node.config.event_pool_manager.sql3lite_worker.execute(
            "update audit_evt set fk_status = 'TS' where request_id = 1"
        )
        self.__audit_node._QSPAuditNode__timeout_stale_requests()
        fst = self.__audit_node.config.event_pool_manager.get_event_by_request_id(
            evt_first['request_id'])
        snd = self.__audit_node.config.event_pool_manager.get_event_by_request_id(
            evt_second['request_id'])
        thrd = self.__audit_node.config.event_pool_manager.get_event_by_request_id(
            evt_third['request_id'])
        self.__audit_node.config.event_pool_manager.close()
        self.assertEqual(fst['fk_status'], 'ER')
        self.assertEqual(snd['fk_status'], 'ER')
        self.assertEqual(thrd['fk_status'], 'AS')

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_contract_audit_request(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        # since we're mocking the smart contract, we should explicitly call its internals
        buggy_contract = resource_uri("DAOBug.sol")
        self.__request_audit(buggy_contract, self.__PRICE)

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__send_done_message(self.__REQUEST_ID)

        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/DAOBug.json")
        self.__assert_all_analyzers(self.__REQUEST_ID)

        compressed_report = TestQSPAuditNode.__compress_report("reports/DAOBug.json")

        # Asserts the database content.
        expected_row = {"request_id": 1,
                        "requestor": self.__config.account,
                        "contract_uri": buggy_contract,
                        "evt_name": "LogAuditAssigned",
                        "block_nbr": "IGNORE",
                        "fk_status": "DN",
                        "fk_type": "AU",
                        "price": str(self.__PRICE),
                        "status_info": "Report successfully submitted",
                        "tx_hash": "IGNORE",
                        "submission_attempts": 1,
                        "is_persisted": 1,
                        "audit_uri": "IGNORE",
                        "audit_hash": "IGNORE",
                        "audit_state": 4,
                        "full_report": "IGNORE",
                        "compressed_report": compressed_report
                        }
        self.assert_event_table_contains(self.__config, [expected_row],
                                         ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_contract_audit_request_dockerhub_fail_isolation(self):
        """
        Tests that a report is generated when the dockerhub fails
        """
        # Replace analyzers with a single dockerhub fail analyzer
        faulty_wrapper = Wrapper(
            wrappers_dir="{0}/tests/resources/wrappers".format(project_root()),
            analyzer_name="dockerhub_fail",
            args="",
            storage_dir="/tmp/{}{}".format(time(), random()),
            timeout_sec=60,
            prefetch=False
        )
        analyzer = Analyzer(faulty_wrapper)
        original_analyzers = self.__audit_node.config._Config__analyzers
        original_analyzers_config = self.__audit_node.config._Config__analyzers_config
        self.__audit_node.config._Config__analyzers = [analyzer]
        self.__audit_node.config._Config__analyzers_config = [{"dockerhub_fail": analyzer}]

        # Since we're mocking the smart contract, we should explicitly call its internals
        buggy_contract = resource_uri("DAOBug.sol")
        self.__request_audit(buggy_contract, self.__PRICE)

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__send_done_message(self.__REQUEST_ID)
        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/DockerhubFail.json")
        self.__assert_all_analyzers(self.__REQUEST_ID)

        # Sets the values back.
        self.__audit_node.config._Config__analyzers = original_analyzers
        self.__audit_node.config._Config__analyzers_config = original_analyzers_config

        compressed_report = TestQSPAuditNode.__compress_report("reports/DockerhubFail.json")

        # Asserts the database content.
        expected_row = {"request_id": 1,
                        "requestor": self.__config.account,
                        "contract_uri": buggy_contract,
                        "evt_name": "LogAuditAssigned",
                        "block_nbr": "IGNORE",
                        "fk_status": "DN",
                        "fk_type": "AU",
                        "price": str(self.__PRICE),
                        "status_info": "Report successfully submitted",
                        "tx_hash": "IGNORE",
                        "submission_attempts": 1,
                        "is_persisted": 1,
                        "audit_uri": "IGNORE",
                        "audit_hash": "IGNORE",
                        "audit_state": 5,
                        "full_report": "IGNORE",
                        "compressed_report": compressed_report
                        }
        self.assert_event_table_contains(self.__config, [expected_row],
                                         ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_contract_audit_request_dockerhub_fail_multiple_analyzers(self):
        """
        Tests that a report is generated when the dockerhub fails
        """
        # Replace analyzers with a single dockerhub fail analyzer
        faulty_wrapper = Wrapper(
            wrappers_dir="{0}/tests/resources/wrappers".format(project_root()),
            analyzer_name="dockerhub_fail",
            args="",
            storage_dir="/tmp/{}{}".format(time(), random()),
            timeout_sec=60,
            prefetch=False
        )
        analyzer = Analyzer(faulty_wrapper)
        original_analyzers = self.__audit_node.config._Config__analyzers
        original_analyzers_config = self.__audit_node.config._Config__analyzers_config
        self.__audit_node.config._Config__analyzers[1] = analyzer
        self.__audit_node.config._Config__analyzers_config[1] = {"dockerhub_fail": analyzer}

        # since we're mocking the smart contract, we should explicitly call its internals
        buggy_contract = resource_uri("DAOBug.sol")
        self.__request_audit(buggy_contract, self.__PRICE)

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__send_done_message(self.__REQUEST_ID)
        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/DockerhubFailAllAnalyzers.json")
        self.__assert_all_analyzers(self.__REQUEST_ID)

        # set the values back
        self.__audit_node.config._Config__analyzers = original_analyzers
        self.__audit_node.config._Config__analyzers_config = original_analyzers_config

        compressed_report = TestQSPAuditNode.__compress_report("reports/DockerhubFailAllAnalyzers.json")

        # asserting the database content
        expected_row = {"request_id": 1,
                        "requestor": self.__config.account,
                        "contract_uri": buggy_contract,
                        "evt_name": "LogAuditAssigned",
                        "block_nbr": "IGNORE",
                        "fk_status": "DN",
                        "fk_type": "AU",
                        "price": str(self.__PRICE),
                        "status_info": "Report successfully submitted",
                        "tx_hash": "IGNORE",
                        "submission_attempts": 1,
                        "is_persisted": 1,
                        "audit_uri": "IGNORE",
                        "audit_hash": "IGNORE",
                        "audit_state": 5,
                        "full_report": "IGNORE",
                        "compressed_report": compressed_report
                        }
        self.assert_event_table_contains(self.__config, [expected_row],
                                          ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_empty_contract_audit_request(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        # since we're mocking the smart contract, we should explicitly call its internals
        empty_contract = resource_uri("Empty.sol")
        self.__request_audit(empty_contract, self.__PRICE)

        # If the report is not submitted, this should timeout the test
        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__send_done_message(self.__REQUEST_ID)

        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/Empty.json")
        self.__assert_all_analyzers(self.__REQUEST_ID)

        compressed_report = TestQSPAuditNode.__compress_report("reports/Empty.json")

        # asserting the database content
        expected_row = {"request_id": 1,
                        "requestor": self.__config.account,
                        "contract_uri": empty_contract,
                        "evt_name": "LogAuditAssigned",
                        "block_nbr": "IGNORE",
                        "fk_status": "DN",
                        "fk_type": "AU",
                        "price": str(self.__PRICE),
                        "status_info": "Report successfully submitted",
                        "tx_hash": "IGNORE",
                        "submission_attempts": 1,
                        "is_persisted": 1,
                        "audit_uri": "IGNORE",
                        "audit_hash": "IGNORE",
                        "audit_state": self.__AUDIT_STATE_ERROR,
                        "full_report": "IGNORE",
                        "compressed_report": compressed_report
                        }
        self.assert_event_table_contains(self.__config, [expected_row],
                                         ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    def test_check_all_threads_return_while_running(self):
        """
        Tests that no exception is thrown when the threads are healthy
        """
        self.__audit_node.check_all_threads()

    def test_check_all_threads_exception(self):
        handles = self.__audit_node._QSPAuditNode__internal_thread_handles
        self.__audit_node.stop()
        self.assertFalse(self.__audit_node.exec)
        # this only sets the exec attribute, the threads remain dead
        self.__audit_node.start()
        self.assertTrue(self.__audit_node.exec)
        # set back all the dead handles
        self.__audit_node._QSPAuditNode__internal_thread_handles = handles
        try:
            self.check_all_threads()
            self.fail("Dead threads were not detected")
        except Exception:
            # expected
            pass

    # TODO(mderka): Disabled flaky test, investigate with QSP-852
    # @timeout(300, timeout_exception=StopIteration)
    # def test_multiple_sequential_requests(self):
    #     """
    #     Tests that bidding happens when multiple request arrive in a row.
    #     """
    #     # since we're mocking the smart contract, we should explicitly call its internals
    #     worker = Sqlite3Worker(self.__config.evt_db_path)
    #     buggy_contract = resource_uri("DAOBug.sol")
    #
    #     # We will request three events in the row without updating the assigned number in the
    #     # smart contract. The node should bid on all of them. We need to interleave them with sleep
    #     # so that there is enough time for the block mined thread to bid and poll. So that the test
    #     # can be executed faster, we will also speed up block polling, and work with Mythril only.
    #     polling_interval = 0.1
    #     original_interval = self.__config.block_mined_polling
    #     original_analyzers = self.__config.analyzers
    #     original_analyzers_config = self.__config.analyzers_config
    #     self.__config._Config__block_mined_polling_interval_sec = polling_interval
    #     self.__config._Config__analyzers = original_analyzers[1:2]
    #     self.__config._Config__analyzers_config = original_analyzers_config[1:2]
    #
    #     self.__set_any_request_available(1)
    #     ids_to_run = [self.__REQUEST_ID, 9, 12]
    #
    #     for id in ids_to_run:
    #         # request and block until a request is made
    #         self.__config.web3_client.eth.waitForTransactionReceipt(
    #             self.__request_assign_and_emit(id, buggy_contract, self.__PRICE, 10))
    #         self.__evt_wait_loop(self.__getNextAuditRequest_filter)
    #         sleep(2)
    #
    #     self.__set_any_request_available(0)
    #
    #     # ensure that we have all requests stored in the database
    #     result = worker.execute("select * from audit_evt")
    #     while len(result) != len(ids_to_run):
    #         sleep(1)
    #         result = worker.execute("select * from audit_evt")
    #     ids = [x['request_id'] for x in result]
    #     for id in ids_to_run:
    #         self.assertTrue(id in ids)
    #
    #     # block until all requests are processed
    #     result = worker.execute("select * from audit_evt where fk_status != 'AS'")
    #     while len(result) != len(ids_to_run):
    #         sleep(1)
    #         result = worker.execute("select * from audit_evt where fk_status != 'AS'")
    #
    #     ids = [x['request_id'] for x in result]
    #     for id in ids_to_run:
    #         # check that the request is done
    #         self.assertTrue(id in ids)
    #         # ensure that submission happens
    #         self.__config.web3_client.eth.waitForTransactionReceipt(
    #             self.__send_done_message(id))
    #         # run assertions
    #         self.__assert_audit_request(id, self.__AUDIT_STATE_SUCCESS,
    #                                     report_file_path="reports/DAOBugMythrilOnly.json",
    #                                     ignore_id=True)
    #         self.__assert_all_analyzers(id)
    #
    #     self.__config._Config__block_mined_polling_interval_sec = original_interval
    #     self.__config._Config__analyzers = original_analyzers
    #     self.__config._Config__analyzers_config = original_analyzers_config

    @timeout(100, timeout_exception=StopIteration)
    def test_buggy_contract_audit_request(self):
        """
        Tests the entire flow of an erroneous audit request, from a request
        to the production of a report and its submission.
        """
        buggy_contract = resource_uri("BasicToken.sol")
        self.__request_audit(buggy_contract, self.__PRICE)

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__send_done_message(self.__REQUEST_ID)

        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/BasicToken.json")

        compressed_report = TestQSPAuditNode.__compress_report("reports/BasicToken.json")

        # Asserts the database content
        expected_row = {"request_id": 1,
                             "requestor": self.__config.account,
                             "contract_uri": buggy_contract,
                             "evt_name": "LogAuditAssigned",
                             "block_nbr": "IGNORE",
                             "fk_status": "DN",
                             "fk_type": "AU",
                             "price": str(self.__PRICE),
                             "status_info": "Report successfully submitted",
                             "tx_hash": "IGNORE",
                             "submission_attempts": 1,
                             "is_persisted": 1,
                             "audit_uri": "IGNORE",
                             "audit_hash": "IGNORE",
                             "audit_state": self.__AUDIT_STATE_ERROR,
                             "full_report": "IGNORE",
                             "compressed_report": compressed_report
                             }
        self.assert_event_table_contains(self.__config, [expected_row],
                                            ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    @timeout(100, timeout_exception=StopIteration)
    def test_target_contract_in_non_raw_text_file(self):
        """
        Tests the entire flow of an audit request of a non-raw text file contract (e.g., HTML), from
        a request to the production of a report and its submission.
        """
        buggy_contract = resource_uri("DappBinWallet.sol")
        self.__request_audit(buggy_contract, self.__PRICE)

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__send_done_message(self.__REQUEST_ID)

        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/DappBinWallet.json")

        compressed_report = TestQSPAuditNode.__compress_report("reports/DappBinWallet.json")

        # Asserts the database content.
        expected_row = {"request_id": 1,
                        "requestor": self.__config.account,
                        "contract_uri": buggy_contract,
                        "evt_name": "LogAuditAssigned",
                        "block_nbr": "IGNORE",
                        "fk_status": "DN",
                        "fk_type": "AU",
                        "price": str(self.__PRICE),
                        "status_info": "Report successfully submitted",
                        "tx_hash": "IGNORE",
                        "submission_attempts": 1,
                        "is_persisted": 1,
                        "audit_uri": "IGNORE",
                        "audit_hash": "IGNORE",
                        "audit_state": self.__AUDIT_STATE_ERROR,
                        "full_report": "IGNORE",
                        "compressed_report": compressed_report
                        }
        self.assert_event_table_contains(self.__config, [expected_row],
                                            ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    def test_run_repeated_start_expecting_fail(self):
        """
        Tests that a second instance of the node cannot be started
        """
        thrown = True
        try:
            self.__audit_node.run()
            thrown = False
        except Exception:
            # the exception is too generic to use self.fail
            pass
        self.assertTrue(thrown, "No exception was thrown when starting multiple instances")

    @timeout(100, timeout_exception=StopIteration)
    def test_restricting_local_max_assigned(self):
        """
        Tests if the limitation on the local maximum assigned requests is in effect
        """

        mocked__get_next_audit_request_called = [False]

        def mocked__get_next_audit_request():
            # this should be unreachable when the limit is reached
            mocked__get_next_audit_request_called[0] = True

        self.assertEqual(int(self.__config.max_assigned_requests), 1)
        # Make sure there anyAvailableRequest returns ready state
        self.__set_any_request_available(1)

        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__set_assigned_request_count(1))

        buggy_contract = resource_uri("DappBinWallet.sol")
        self.__request_assign_and_emit(self.__REQUEST_ID, buggy_contract, self.__PRICE, 1)
        with mock.patch(
                'audit.threads.poll_requests_thread.PollRequestsThread.'
                '_PollRequestsThread__get_next_audit_request',
                side_effect=mocked__get_next_audit_request):
            # Make sure there is enough time for mining poll to call QSPAuditNode.__check_then_bid_audit
            # request
            sleep(self.__config.block_mined_polling + 1)
            self.__evt_wait_loop(self.__submitReport_filter)
            self.__config.web3_client.eth.waitForTransactionReceipt(
                self.__set_assigned_request_count(0))
            self.__send_done_message(self.__REQUEST_ID)

        # This is a critical line to be called as the node did all it audits and starts bidding
        # again
        self.__evt_wait_loop(self.__getNextAuditRequest_filter)
        self.__set_any_request_available(0)
        # an extra call to get_next_audit is no accepted
        self.assertFalse(mocked__get_next_audit_request_called[0])

    @timeout(45, timeout_exception=StopIteration)
    def test_timeout_on_complex_file(self):
        """
        Tests if the analyzer throttles the execution and generates error message
        """

        # rewiring configs
        original_timeouts = []
        for i in range(0, len(self.__config.analyzers)):
            # It's an expected behaviour
            analyzer_name = self.__config.analyzers[i].wrapper.analyzer_name
            self.assertEqual(
                self.__audit_node.config.analyzers[i].wrapper._Wrapper__timeout_sec,
                self.__audit_node.config._Config__analyzers_config[i][analyzer_name][
                    'timeout_sec'])
            original_timeouts.append(
                self.__audit_node.config.analyzers[i].wrapper._Wrapper__timeout_sec)
            self.__audit_node.config.analyzers[i].wrapper._Wrapper__timeout_sec = 6
            self.__audit_node.config._Config__analyzers_config[i][analyzer_name][
                'timeout_sec'] = 3

        contract = resource_uri("kyber.sol")
        self.__request_audit(contract, self.__PRICE)

        self.__evt_wait_loop(self.__submitReport_filter)

        self.__send_done_message(self.__REQUEST_ID)
        self.__assert_audit_request_report(self.__REQUEST_ID,
                                           report_file_path="reports/kyber.json")
        # setting back the configurations
        for i in range(0, len(original_timeouts)):
            self.__audit_node.config.analyzers[i].wrapper._Wrapper__timeout_sec = \
                original_timeouts[i]
            analyzer_name = self.__config.analyzers[i].wrapper.analyzer_name
            self.__audit_node.config._Config__analyzers_config[i][
                analyzer_name]['timeout_sec'] = original_timeouts[i]

        compressed_report = TestQSPAuditNode.__compress_report("reports/kyber.json")

        # Asserts the database content.
        expected_row = {"request_id": 1,
                        "requestor": self.__config.account,
                        "contract_uri": contract,
                        "evt_name": "LogAuditAssigned",
                        "block_nbr": "IGNORE",
                        "fk_status": "DN",
                        "fk_type": "AU",
                        "price": str(self.__PRICE),
                        "status_info": "Report successfully submitted",
                        "tx_hash": "IGNORE",
                        "submission_attempts": 1,
                        "is_persisted": 1,
                        "audit_uri": "IGNORE",
                        "audit_hash": "IGNORE",
                        "audit_state": self.__AUDIT_STATE_ERROR,
                        "full_report": "IGNORE",
                        "compressed_report": compressed_report
                        }
        self.assert_event_table_contains(self.__config, [expected_row],
                                            ignore_keys=[key for key in expected_row if expected_row[key] == "IGNORE"])

    @timeout(30, timeout_exception=StopIteration)
    def test_configuration_checks(self):
        """
        Tests configuration sanity checks.
        Since this test requires loading the QuantstampAuditData contract, it is better here than
        test_config.py.
        """
        config = self.__audit_node.config
        config_utils = ConfigUtils(config.node_version)
        try:
            temp = config.submission_timeout_limit_blocks
            config._Config__submission_timeout_limit_blocks = 2
            config_utils.check_configuration_settings(config)
            self.fail("Configuration error should have been raised.")
        except ConfigurationException:
            config._Config__submission_timeout_limit_blocks = temp
        try:
            temp = config.submission_timeout_limit_blocks
            config._Config__submission_timeout_limit_blocks = 123
            config_utils.check_configuration_settings(config)
            self.fail("Configuration error should have been raised.")
        except ConfigurationException:
            config._Config__submission_timeout_limit_blocks = temp
        for i in range(0, len(self.__audit_node.config.analyzers)):
            try:
                temp = self.__audit_node.config.analyzers[
                    i].wrapper._Wrapper__timeout_sec
                self.__audit_node.config.analyzers[
                    i].wrapper._Wrapper__timeout_sec = 123456
                config_utils.check_configuration_settings(config)
                self.fail("Configuration error should have been raised.")
            except ConfigurationException:
                self.__audit_node.config.analyzers[
                    i].wrapper._Wrapper__timeout_sec = temp

    ##############################################
    # Helper methods (class/static level)
    ##############################################

    @staticmethod
    def __compress_report(report_path_uri):
        full_report = load_json(fetch_file(resource_uri(report_path_uri)))
        encoder = ReportEncoder()
        return encoder.compress_report(full_report, full_report['request_id'])

    ##############################################
    # Helper methods (object level)
    ##############################################

    def __assert_audit_request_report(self, request_id, report_file_path=None, ignore_id=False):
        audit = self.__fetch_audit_from_db(request_id)
        if report_file_path is not None:
            audit_file = fetch_file(audit['audit_uri'])
            self.assertEqual(digest_file(audit_file), audit['audit_hash'])
            self.compare_json(audit_file, report_file_path, ignore_id=ignore_id)

    def __assert_all_analyzers(self, request_id):
        """
        Asserts that all configured analyzers were executed and are included in the report.
        """
        row = self.__fetch_audit_from_db(request_id)

        audit_uri = row['audit_uri']
        audit_file = fetch_file(audit_uri)
        actual_json = load_json(audit_file)
        executed_analyzers = [x['analyzer']['name'] for x in actual_json['analyzers_reports']]
        for analyzer in self.__config.analyzers_config:
            name, conf = list(analyzer.items())[0]
            self.assertTrue(name in executed_analyzers)

    def __evt_wait_loop(self, current_filter):
        events = current_filter.get_new_entries()
        while not bool(events):
            sleep(TestQSPAuditNode.__SLEEP_INTERVAL)
            events = current_filter.get_new_entries()
        return events

    def __fetch_audit_from_db(self, request_id):
        sql3lite_worker = self.__config.event_pool_manager.sql3lite_worker

        # Busy waits on receiving events up to the configured timeout (60s)
        row = None
        while True:
            row = get_first(
                sql3lite_worker.execute("select * from audit_evt where fk_status = 'DN' "
                                        "and request_id = {}".format(request_id)))
            if row != {} and row['request_id'] == request_id:
                break
            else:
                sleep(TestQSPAuditNode.__SLEEP_INTERVAL)
        return row

    def __mk_unique_storage_dir(self):
        """
        Generates a unique directory for each test run
        """
        for analyzer in self.__audit_node.config.analyzers:
            analyzer.wrapper._Wrapper__storage_dir += "/{}{}".format(time(), random())

    def __request_audit(self, contract_uri, price):
        """
        Emulates requesting a new audit. Allows the node to bid and retrieve the audit. Then stops
        bidding by removing anyRequestAvailable marker.
        """
        # this block number is high enough for the tests not to time out on this request
        request_block_number = self.__config.web3_client.eth.blockNumber
        result = self.__request_assign_and_emit(
            self.__REQUEST_ID,
            contract_uri,
            price,
            request_block_number)

        self.__set_any_request_available(1)
        self.__evt_wait_loop(self.__setAnyRequestAvailableResult_filter)
        self.__evt_wait_loop(self.__getNextAuditRequest_filter)
        self.__set_any_request_available(0)
        self.__evt_wait_loop(self.__setAnyRequestAvailableResult_filter)
        return result

    def __request_assign_and_emit(self, request_id, contract_uri, price, request_block_number):
        """
        Emulates assigning a request for a given target contract by submitting the appropriate
        event.
        """
        requestor = self.__config.account
        auditor = self.__config.account
        return safe_transact(
            self.__config.audit_contract.functions.assignAuditAndEmit(
                request_id,
                requestor,
                auditor,
                contract_uri,
                price,
                request_block_number),
            {"from": requestor}
        )

    def __set_any_request_available(self, number):
        tx_hash = safe_transact(
            self.__config.audit_contract.functions.setAnyRequestAvailableResult(number),
            {"from": self.__config.account}
        )
        self.__config.web3_client.eth.waitForTransactionReceipt(tx_hash)
        return tx_hash

    def __send_done_message(self, request_id):
        return safe_transact(
            self.__config.audit_contract.functions.emitLogAuditFinished(
                request_id,
                self.__config.account,
                0,
                ""),
            {"from": self.__config.account}
        )

    def __set_assigned_request_count(self, num, gas_price=0):
        return safe_transact(
            self.__config.audit_contract.functions.setAssignedRequestCount(
                self.__config.account,
                num),
            {"from": self.__config.account, "gasPrice": gas_price}
        )


if __name__ == '__main__':
    unittest.main()
