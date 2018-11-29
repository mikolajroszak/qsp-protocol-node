####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Tests the flow of receiving audit requests and
their flow within the QSP audit node
"""
import contextlib
import ntpath
import os
import unittest
import structlog

from audit import QSPAuditNode
from audit import ExecutionException
from config import ConfigFactory, ConfigUtils, ConfigurationException
from dpath.util import get
from helpers.resource import (
    resource_uri,
    project_root,
)
from upload import DummyProvider

from utils.eth.singleton_lock import SingletonLock
from utils.io import fetch_file, digest_file, load_json
from utils.db import get_first
from utils.db import Sqlite3Worker

from deepdiff import DeepDiff
from pprint import pprint
from solc import compile_files
from time import sleep
from timeout_decorator import timeout
from threading import Thread
from utils.eth import DeduplicationException
from unittest import mock
from web3.utils.threads import Timeout


class TestQSPAuditNode(unittest.TestCase):
    __AUDIT_STATE_SUCCESS = 4
    __AUDIT_STATE_ERROR = 5
    __AVAILABLE_AUDIT_STATE_READY = 1
    __AVAILABLE_AUDIT_STATE_ERROR = 0
    __REQUEST_ID = 1
    __PRICE = 100
    __SLEEP_INTERVAL = 0.01

    @classmethod
    def __clean_up_file(cls, path):
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)

    @staticmethod
    def __safe_transact(contract_entity, tx_args):
        """
        The contract_entity should already be invoked, so that we can immediately call transact
        """
        try:
            SingletonLock.instance().lock.acquire()
            return contract_entity.transact(tx_args)
        except Exception as e:
            print("!!!!!!! Safe transaction in tests failed")
            raise e
        finally:
            try:
                SingletonLock.instance().lock.release()
            except Exception as error:
                print("Error when releasing a lock in test {0}".format(str(error)))

    @staticmethod
    def __load_audit_contract_from_src(web3_client, contract_src_uri, contract_name,
                                       constructor_from):
        """
        Loads the QuantstampAuditMock contract from source code returning the (address, contract)
        pair.
        """
        audit_contract_src = fetch_file(contract_src_uri)
        contract_dict = compile_files([audit_contract_src])
        contract_id = "{0}:{1}".format(
            contract_src_uri,
            contract_name,
        )
        contract_interface = contract_dict[contract_id]

        # deploy the audit contract
        audit_contract = web3_client.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )
        tx_hash = TestQSPAuditNode.__safe_transact(audit_contract.constructor(),
                                                   {'from': constructor_from, 'gasPrice': 0})
        receipt = web3_client.eth.getTransactionReceipt(tx_hash)
        address = receipt['contractAddress']
        audit_contract = web3_client.eth.contract(
            abi=contract_interface['abi'],
            address=address,
        )
        return address, audit_contract

    def __compare_json(self, audit_file, report_file_path, json_loaded=False, ignore_id=False):
        if not json_loaded:
            actual_json = load_json(audit_file)
        else:
            actual_json = audit_file
        expected_json = load_json(fetch_file(resource_uri(report_file_path)))
        if ignore_id:
            expected_json['request_id'] = actual_json['request_id']
        diff = DeepDiff(actual_json,
                        expected_json,
                        exclude_paths={
                            "root['contract_uri']",
                            # There is no keystore used for testing. Accounts
                            # are dynamic and therefore cannot be compared
                            "root['auditor']",
                            "root['requestor']",
                            # Path is different depending on whether running inside Docker
                            "root['timestamp']",
                            "root['start_time']",
                            "root['end_time']",
                            "root['analyzers_reports'][0]['analyzer']['command']",
                            "root['analyzers_reports'][0]['coverages'][0]['file']",
                            "root['analyzers_reports'][0]['potential_vulnerabilities'][0]['file']",
                            "root['analyzers_reports'][0]['start_time']",
                            "root['analyzers_reports'][0]['end_time']",
                            "root['analyzers_reports'][1]['analyzer']['command']",
                            "root['analyzers_reports'][1]['coverages'][0]['file']",
                            "root['analyzers_reports'][1]['potential_vulnerabilities'][0]['file']",
                            "root['analyzers_reports'][1]['start_time']",
                            "root['analyzers_reports'][1]['end_time']",
                            "root['analyzers_reports'][2]['analyzer']['command']",
                            "root['analyzers_reports'][2]['coverages'][0]['file']",
                            "root['analyzers_reports'][2]['potential_vulnerabilities'][0]['file']",
                            "root['analyzers_reports'][2]['start_time']",
                            "root['analyzers_reports'][2]['end_time']",
                        }
                    )
        pprint(diff)
        self.assertEqual(diff, {})
        self.assertEqual(ntpath.basename(actual_json['contract_uri']),
                         ntpath.basename(expected_json['contract_uri']))

    @classmethod
    def fetch_config(cls):
        # create config from file, the contract is not provided and will be injected separately
        config_file_uri = resource_uri("test_config.yaml")
        config = ConfigFactory.create_from_file(config_file_uri, os.getenv("QSP_ENV", default="dev"),
                                                validate_contract_settings=False)
        # compile and inject contract
        contract_source_uri = "./tests/resources/QuantstampAuditMock.sol"
        contract_metadata_uri = "./tests/resources/QuantstampAudit-metadata.json"
        audit_contract_metadata = load_json(fetch_file(contract_metadata_uri))
        audit_contract_name = get(audit_contract_metadata, '/contractName')

        addr, contract = \
            TestQSPAuditNode.__load_audit_contract_from_src(
                config.web3_client,
                contract_source_uri,
                audit_contract_name,
                config.account)

        config._Config__audit_contract_address = addr
        config._Config__audit_contract = contract

        config_utils = ConfigUtils(config.node_version)
        config_utils.check_configuration_settings(config)
        return config

    @classmethod
    def setUpClass(cls):
        config = TestQSPAuditNode.fetch_config()
        # Assures structlog has been minimally configured
        structlog.configure_once(
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
        )
        TestQSPAuditNode.__clean_up_file(config.evt_db_path)

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__config = TestQSPAuditNode.fetch_config()
        self.__audit_node = QSPAuditNode(self.__config)

        # Forces analyzer wrapper to always execute their `once` script prior
        # to executing `run`
        for analyzer in self.__config.analyzers:
            TestQSPAuditNode.__clean_up_file(analyzer.wrapper.storage_dir + '/.once')

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
        while not self.__audit_node.audit_node_initialized:
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
        TestQSPAuditNode.__clean_up_file(self.__config.evt_db_path)

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
        manager = self.__audit_node._QSPAuditNode__config.event_pool_manager
        self.__audit_node._QSPAuditNode__config._Config__event_pool_manager = ManagerMock()
        self.__audit_node.stop()
        self.__audit_node._QSPAuditNode__config._Config__event_pool_manager = manager

        self.__audit_node._QSPAuditNode__config._Config__web3_client = Web3Mock(EthMock())
        self.__audit_node._QSPAuditNode__config._Config__submission_timeout_limit_blocks = 10
        self.__audit_node._QSPAuditNode__config._Config__block_discard_on_restart = 2
        # certainly times out
        evt_first = {'request_id': 1,
                     'requestor': 'x',
                     'contract_uri': 'x',
                     'evt_name': 'x',
                     'block_nbr': 10,
                     'status_info': 'x',
                     'price': 12}
        # last block to time out
        evt_second = {'request_id': 17,
                      'requestor': 'x',
                      'contract_uri': 'x',
                      'evt_name': 'x',
                      'block_nbr': 90 + 2,
                      'status_info': 'x',
                      'price': 12}
        # first block not to time out
        evt_third = {'request_id': 18,
                     'requestor': 'x',
                     'contract_uri': 'x',
                     'evt_name': 'x',
                     'block_nbr': 91 + 2,
                     'status_info': 'x',
                     'price': 12}
        self.__audit_node._QSPAuditNode__config.event_pool_manager.add_evt_to_be_assigned(evt_first)
        self.__audit_node._QSPAuditNode__config.event_pool_manager.add_evt_to_be_assigned(
            evt_second
        )
        self.__audit_node._QSPAuditNode__config.event_pool_manager.add_evt_to_be_assigned(evt_third)
        self.__audit_node._QSPAuditNode__config.event_pool_manager.sql3lite_worker.execute(
            "update audit_evt set fk_status = 'TS' where request_id = 1"
        )
        self.__audit_node._QSPAuditNode__timeout_stale_requests()
        fst = self.__audit_node._QSPAuditNode__config.event_pool_manager.get_event_by_request_id(
            evt_first['request_id'])
        snd = self.__audit_node._QSPAuditNode__config.event_pool_manager.get_event_by_request_id(
            evt_second['request_id'])
        thrd = self.__audit_node._QSPAuditNode__config.event_pool_manager.get_event_by_request_id(
            evt_third['request_id'])
        self.__audit_node._QSPAuditNode__config.event_pool_manager.close()
        self.assertEqual(fst['fk_status'], 'ER')
        self.assertEqual(snd['fk_status'], 'ER')
        self.assertEqual(thrd['fk_status'], 'AS')

    @timeout(10, timeout_exception=StopIteration)
    def test_check_then_do_audit_request_exceptions(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        get_next_audit_request = self.__audit_node._QSPAuditNode__get_next_audit_request

        def mocked__get_next_audit_request():
            raise Exception('mocked exception')

        self.__audit_node._QSPAuditNode__get_next_audit_request = mocked__get_next_audit_request
        self.__set_any_request_available(1)
        self.__audit_node._QSPAuditNode__check_then_do_audit_request()
        self.__set_any_request_available(0)
        self.__audit_node._QSPAuditNode__get_next_audit_request = get_next_audit_request

    @timeout(10, timeout_exception=StopIteration)
    def test_check_then_do_audit_request_deduplication_exceptions(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        get_next_audit_request = self.__audit_node._QSPAuditNode__get_next_audit_request

        def mocked__get_next_audit_request():
            raise DeduplicationException('mocked exception')

        self.__audit_node._QSPAuditNode__get_next_audit_request = mocked__get_next_audit_request
        self.__set_any_request_available(1)
        self.__audit_node._QSPAuditNode__check_then_do_audit_request()
        self.__set_any_request_available(0)
        self.__audit_node._QSPAuditNode__get_next_audit_request = get_next_audit_request

    @timeout(10, timeout_exception=StopIteration)
    def test_check_and_update_min_price_call(self):
        value = self.__config.min_price_in_qsp + 1
        with mock.patch('audit.audit.mk_read_only_call', return_value=value) as mocked_read, \
             mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            self.__audit_node._QSPAuditNode__check_and_update_min_price()
            mocked_sign.assert_called()

    @timeout(10, timeout_exception=StopIteration)
    def test_update_min_price_timeout_exception(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch('audit.audit.mk_read_only_call', return_value=-1) as mocked_read, \
             mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = Timeout()
                self.__audit_node._QSPAuditNode__update_min_price()
                self.fail("An exception should have been thrown")
            except Timeout as e:
                pass

    @timeout(10, timeout_exception=StopIteration)
    def test_update_min_price_deduplication_exception(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch('audit.audit.mk_read_only_call', return_value=-1) as mocked_read, \
             mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = DeduplicationException()
                self.__audit_node._QSPAuditNode__update_min_price()
                self.fail("An exception should have been thrown")
            except DeduplicationException as e:
                pass

    @timeout(10, timeout_exception=StopIteration)
    def test_update_min_price_other_exception(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        with mock.patch('audit.audit.mk_read_only_call', return_value=-1) as mocked_read, \
                mock.patch('audit.audit.send_signed_transaction') as mocked_sign:
            try:
                mocked_sign.side_effect = ValueError()
                self.__audit_node._QSPAuditNode__update_min_price()
                self.fail("An exception should have been thrown")
            except ValueError as e:
                pass

    @timeout(20, timeout_exception=StopIteration)
    def test_on_audit_assigned(self):
        # The following causes an exception in the auditing node, but it should be caught and
        # should not propagate
        self.__audit_node._QSPAuditNode__on_audit_assigned({})
        # This causes an auditor id mismatch
        evt = {'args': {'auditor': 'this is not me', 'requestId': 1}}
        self.__audit_node._QSPAuditNode__on_audit_assigned(evt)
        # test real auditor id with case mismatch and successful submit
        buggy_contract = resource_uri("DAOBug.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(buggy_contract, self.__PRICE)
        )
        auditor_id = self.__audit_node._QSPAuditNode__config.account.upper()
        evt = {'args': {'auditor': auditor_id, 'requestId': 1, 'price': self.__PRICE,
                        'requestor': auditor_id, 'uri': buggy_contract}, 'blockNumber': 1}
        self.__audit_node._QSPAuditNode__on_audit_assigned(evt)
        sql3lite_worker = self.__config.event_pool_manager.sql3lite_worker
        row = get_first(sql3lite_worker.execute("select * from audit_evt"))
        self.assertEqual(row['fk_status'], 'AS')

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_contract_audit_request(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        # since we're mocking the smart contract, we should explicitly call its internals
        buggy_contract = resource_uri("DAOBug.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(buggy_contract, self.__PRICE)
        )

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))

        self.__assert_audit_request(self.__REQUEST_ID, self.__AUDIT_STATE_SUCCESS,
                                    report_file_path="reports/DAOBug.json")
        self.__assert_all_analyzers(self.__REQUEST_ID)

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_contract_audit_request_with_disabled_upload(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        # rewires the config
        self.__audit_node._QSPAuditNode__config._Config__report_upload_is_enabled = False
        self.__audit_node._QSPAuditNode__config._Config__report_uploader_provider_name = ""
        self.__audit_node._QSPAuditNode__config._Config__report_uploader_provider_args = {}
        self.__audit_node._QSPAuditNode__config._Config__report_uploader = DummyProvider()

        # since we're mocking the smart contract, we should explicitly call its internals
        buggy_contract = resource_uri("DAOBug.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(buggy_contract, self.__PRICE)
        )

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))

        self.__assert_audit_request(self.__REQUEST_ID, self.__AUDIT_STATE_SUCCESS)

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_empty_contract_audit_request(self):
        """
        Tests the entire flow of a successful audit request, from a request
        to the production of a report and its submission.
        """
        # since we're mocking the smart contract, we should explicitly call its internals
        empty_contract = resource_uri("Empty.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(empty_contract, self.__PRICE)
        )

        # If the report is not submitted, this should timeout the test
        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))

        self.__assert_audit_request(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR,
                                     report_file_path="reports/Empty.json")
        self.__assert_all_analyzers(self.__REQUEST_ID)

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
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(buggy_contract, self.__PRICE)
        )

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))

        self.__assert_audit_request(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR,
                                    report_file_path="reports/BasicToken.json")

    @timeout(100, timeout_exception=StopIteration)
    def test_target_contract_in_non_raw_text_file(self):
        """
        Tests the entire flow of an audit request of a non-raw text file contract (e.g., HTML), from
        a request to the production of a report and its submission.
        """
        buggy_contract = resource_uri("DappBinWallet.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(buggy_contract, self.__PRICE)
        )

        self.__evt_wait_loop(self.__submitReport_filter)

        # NOTE: if the audit node later requires the stubbed fields, this will have to change a bit
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))

        self.__assert_audit_request(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR,
                                    report_file_path="reports/DappBinWallet.json")

    @timeout(300, timeout_exception=StopIteration)
    def test_analyzer_produces_metadata_for_errors(self):
        """
        Tests that analyzers produce their metadata even when failure occurs
        """
        buggy_contract = resource_uri("BasicToken.sol")
        buggy_contract_file = fetch_file(buggy_contract)
        # directly calling this function to avoid compilation checks;
        # this will cause error states for the analyzers
        report = self.__audit_node.get_audit_report_from_analyzers(buggy_contract_file,
                                                                   "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                                                                   buggy_contract,
                                                                   1)
        self.__compare_json(report, "reports/BasicTokenErrorWithMetadata.json", json_loaded=True)

    @timeout(5, timeout_exception=StopIteration)
    def test_run_audit_evt_thread(self):
        """
        Tests that the run_evt_thread dies upon an internal exception
        """
        # An exception should be re-thrown inside the thread
        thread = self.__audit_node._QSPAuditNode__run_audit_evt_thread(None, None, None)
        thread.join()
        self.assertFalse(thread.is_alive(), "Thread was supposed be terminated by an exception")

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

    # Variable to be passed to the mocked function
    __mocked__get_next_audit_request_called = False

    def __set_any_request_available(self, number):
        tx_hash = TestQSPAuditNode.__safe_transact(
            self.__config.audit_contract.functions.setAnyRequestAvailableResult(number),
            {"from": self.__config.account}
        )
        self.__config.web3_client.eth.waitForTransactionReceipt(tx_hash)
        return tx_hash

    @timeout(40, timeout_exception=StopIteration)
    def test_restricting_local_max_assigned(self):
        """
        Tests if the limitation on the local maximum assigned requests is in effect
        """

        # Mocking the QSPAuditNode.__get_next_audit_request. This function is supposed to be called
        # if the limit is not reached.
        original__get_next_audit_request = self.__audit_node._QSPAuditNode__get_next_audit_request

        def mocked__get_next_audit_request():
            # this should be unreachable when the limit is reached
            self.__mocked__get_next_audit_request_called = True

        self.assertEqual(int(self.__config.max_assigned_requests), 1)

        # Make sure there anyAvailableRequest returns ready state
        self.__set_any_request_available(1)

        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__set_assigned_request_count(1))

        buggy_contract = resource_uri("DappBinWallet.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_assign_and_emit(self.__REQUEST_ID, buggy_contract, self.__PRICE, 100)
        )

        # Node should not ask for further request
        self.__audit_node._QSPAuditNode__get_next_audit_request = mocked__get_next_audit_request

        # Make sure there is enough time for mining poll to call QSPAuditNode.__check_then_bid_audit
        # request
        sleep(self.__config.block_mined_polling + 1)

        self.__evt_wait_loop(self.__submitReport_filter)

        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__set_assigned_request_count(0))

        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))

        # Restore QSPAuditNode.__get_next_audit_request actual implementation
        self.__audit_node._QSPAuditNode__get_next_audit_request = original__get_next_audit_request

        # This is a critical line to be called as the node did all it audits and starts bidding
        # again
        self.__evt_wait_loop(self.__getNextAuditRequest_filter)
        self.__set_any_request_available(0)

        # an extra call to get_next_audit is no accepted
        self.assertFalse(self.__mocked__get_next_audit_request_called)

    @timeout(30, timeout_exception=StopIteration)
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
                self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec,
                self.__audit_node._QSPAuditNode__config._Config__analyzers_config[i][analyzer_name][
                    'timeout_sec'])
            original_timeouts.append(
                self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec)
            self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec = 6
            self.__audit_node._QSPAuditNode__config._Config__analyzers_config[i][analyzer_name][
                'timeout_sec'] = 3

        contract = resource_uri("kyber.sol")
        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__request_audit(contract, self.__PRICE))

        self.__evt_wait_loop(self.__submitReport_filter)

        self.__config.web3_client.eth.waitForTransactionReceipt(
            self.__send_done_message(self.__REQUEST_ID))
        self.__assert_audit_request(self.__REQUEST_ID, self.__AUDIT_STATE_ERROR,
                                    report_file_path="reports/kyber.json")
        # setting back the configurations
        for i in range(0, len(original_timeouts)):
            self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec = \
                original_timeouts[i]
            analyzer_name = self.__config.analyzers[i].wrapper.analyzer_name
            self.__audit_node._QSPAuditNode__config._Config__analyzers_config[i][
                analyzer_name]['timeout_sec'] = original_timeouts[i]

    @timeout(30, timeout_exception=StopIteration)
    def test_change_min_price(self):
        """
        Tests that the node updates the min_price on the blockchain if the config value changes
        """
        self.__audit_node._QSPAuditNode__config._Config__min_price_in_qsp = 1
        # this makes an one-off call
        self.__audit_node._QSPAuditNode__update_min_price()
        success = False
        while not success:
            events = self.__evt_wait_loop(self.__setAuditNodePrice_filter)
            for event in events:
                self.assertEqual(event['event'], 'setAuditNodePrice_called')
                if event['args']['price'] == 10 ** 18:
                    success = True
                    break
            if not success:
                sleep(TestQSPAuditNode.__SLEEP_INTERVAL)

    @timeout(10, timeout_exception=StopIteration)
    def test_not_whitelisted(self):
        # the address has to have fixed length, do not truncate
        address = '0x0000000000000000000000000000000000000000'
        self.assertFalse(self.__audit_node._QSPAuditNode__check_whitelist(address),
                         "Address 0x0 is not whitelisted")

    @timeout(10, timeout_exception=StopIteration)
    def test_not_whitelisted_run(self):
        self.__audit_node.stop()
        # the address has to have fixed length, do not truncate
        address = '0x0000000000000000000000000000000000000000'
        self.__audit_node.config._Config__account = address
        try:
            self.__audit_node.run()
            self.fail("This should throw an error")
        except ExecutionException:
            pass

    @timeout(30, timeout_exception=StopIteration)
    def test_gas_price_computation_static(self):
        num_blocks = 5
        # fill the blockchain with some transactions
        for i in range(num_blocks):
            self.__config.web3_client.eth.waitForTransactionReceipt(
                self.__set_assigned_request_count(0, i * 1000))
        self.__config._Config__default_gas_price_wei = 12345
        self.__config._Config__gas_price_strategy = "static"
        self.__audit_node._QSPAuditNode__compute_gas_price()
        self.assertEqual(self.__config.gas_price_wei, 12345)

    @timeout(30, timeout_exception=StopIteration)
    def test_gas_price_computation_empty_blockchain(self):
        # tests for errors when there are too few blocks in the blockchain history
        self.__audit_node._QSPAuditNode__compute_gas_price()

    @timeout(30, timeout_exception=StopIteration)
    def test_configuration_checks(self):
        """
        Tests configuration sanity checks.
        Since this test requires loading the QuantstampAuditData contract, it is better here than
        test_config.py.
        """
        config = self.__audit_node._QSPAuditNode__config
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
        for i in range(0, len(self.__audit_node._QSPAuditNode__config.analyzers)):
            try:
                temp = self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec
                self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec = 123456
                config_utils.check_configuration_settings(config)
                self.fail("Configuration error should have been raised.")
            except ConfigurationException:
                self.__audit_node._QSPAuditNode__config.analyzers[i].wrapper._Wrapper__timeout_sec = temp

    def __assert_audit_request(self, request_id, expected_audit_state, report_file_path=None,
                               ignore_id=False):
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

        self.assertEqual(row['evt_name'], "LogAuditAssigned")

        # FIXME: add range validation
        self.assertTrue(int(row['block_nbr']) > 0)

        self.assertEqual(int(row['price']), 100)
        self.assertEqual(row['submission_attempts'], 1)
        self.assertEqual(row['is_persisted'], True)

        self.assertTrue(row['tx_hash'] is not None)
        self.assertTrue(row['contract_uri'] is not None)

        audit_state = row['audit_state']
        self.assertEqual(audit_state, expected_audit_state)

        audit_uri = row['audit_uri']
        if report_file_path is not None:
            audit_file = fetch_file(audit_uri)
            self.assertEqual(digest_file(audit_file), row['audit_hash'])
            self.__compare_json(audit_file, report_file_path, ignore_id=ignore_id)
        else:
            self.assertEqual(audit_uri, "Not available. Full report was not uploaded")

    def __assert_all_analyzers(self, request_id):
        """
        Asserts that all configured analyzers were executed and are included in the report.
        """
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

    def __request_audit(self, contract_uri, price):
        """
        Emulates requesting a new audit. Allows the node to bid and retrieve the audit. Then stops
        bidding by removing anyRequestAvailable marker.
        """
        # this block number is high enough for the tests not to time out on this request
        request_block_number = 40
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
        return TestQSPAuditNode.__safe_transact(
            self.__config.audit_contract.functions.assignAuditAndEmit(
                request_id,
                requestor,
                auditor,
                contract_uri,
                price,
                request_block_number),
            {"from": requestor}
        )

    def __send_done_message(self, request_id):
        return TestQSPAuditNode.__safe_transact(
            self.__config.audit_contract.functions.emitLogAuditFinished(
                request_id,
                self.__config.account,
                0,
                ""),
            {"from": self.__config.account}
        )

    def __set_assigned_request_count(self, num, gas_price=0):
        return TestQSPAuditNode.__safe_transact(
            self.__config.audit_contract.functions.setAssignedRequestCount(
                self.__config.account,
                num),
            {"from": self.__config.account, "gasPrice": gas_price}
        )


if __name__ == '__main__':
    unittest.main()
