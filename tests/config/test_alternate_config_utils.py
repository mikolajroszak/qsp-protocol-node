import unittest
import os

from config import ConfigUtils
from config import ConfigurationException
from upload import S3Provider
from helpers.resource import resource_uri
from utils.eth.wallet_session_manager import DummyWalletSessionManager
from utils.eth.wallet_session_manager import WalletSessionManager
from streaming import CloudWatchProvider
from web3 import (
    Web3,
    TestRPCProvider,
    HTTPProvider,
    IPCProvider,
    EthereumTesterProvider,
)


class ConfigStub:
    """
    TODO(mderka): Replace this with real config class when it become available in later PRs
    """

    def __init__(self, abi, abi_uri, contract_address, src, src_uri):
        self.has_audit_contract_abi = abi
        self.has_audit_contract_src = src
        self.audit_contract_abi_uri = abi_uri
        self.audit_contract_address = contract_address
        self.audit_contract_src_uri = src_uri


class TestConfigUtil(unittest.TestCase):

    def setUp(self):
        self.config_utils = ConfigUtils()

    def test_create_report_uploader_provider_ok(self):
        """
        Tests that the S3Provider can be created and is properly returend.
        """
        report_uploader_provider_name = "S3Provider"
        report_uploader_provider_args = {"bucket_name": "test-bucket"}
        result = self.config_utils.create_report_uploader_provider(report_uploader_provider_name,
                                                                   report_uploader_provider_args)
        self.assertTrue(isinstance(result, S3Provider), "The created provider is not an S3Provider")

    def test_create_report_uploader_provider_not_ok(self):
        """
        Tests that wrong upload provider specification causes an exception being thrown.
        """
        report_uploader_provider_name = "nonsense"
        report_uploader_provider_args = {}
        try:
            self.config_utils.create_report_uploader_provider(report_uploader_provider_name,
                                                              report_uploader_provider_args)
            self.fail("Succeeded to create upload provider without proper provider name.")
        except ConfigurationException:
            # expected
            pass

    def test_create_logging_streaming_provider_ok(self):
        """
        Tests that the CloudWatch provider can be created and is properly returned.
        """
        streaming_provider_name = "CloudWatchProvider"
        streaming_provider_args = {'log_group': 'grp', 'log_stream': 'stream',
                                   'send_interval_seconds': 10}
        result = self.config_utils.create_logging_streaming_provider(streaming_provider_name,
                                                                     streaming_provider_args)
        self.assertTrue(isinstance(result, CloudWatchProvider),
                        "The created provider is not a CloudWatchProvider")

    def test_create_logging_streaming_provider_not_ok(self):
        """
        Tests that wrong streaming provider specification causes an exception being thrown.
        """
        streaming_provider_name = "nonsens"
        streaming_provider_args = {'log_group': 'grp', 'log_stream': 'stream',
                                   'send_interval_seconds': 10}
        try:
            self.config_utils.create_logging_streaming_provider(streaming_provider_name,
                                                                streaming_provider_args)
            self.fail("Succeeded to create streaming provider without proper provider name.")
        except ConfigurationException:
            # expected
            pass

    def test_create_wallet_session_manager_dummy(self):
        """
        Tests that testing ETH provider names create dummy wallet managers.
        """
        name = "EthereumTesterProvider"
        result = self.config_utils.create_wallet_session_manager(name)
        self.assertTrue(isinstance(result, DummyWalletSessionManager),
                        "The wallet manager is not a DummyWalletSessionManager")
        name = "TestRPCProvider"
        result = self.config_utils.create_wallet_session_manager(name)
        self.assertTrue(isinstance(result, DummyWalletSessionManager),
                        "The wallet manager is not a DummyWalletSessionManager")

    def test_create_wallet_session_manager_real(self):
        """
        Tests that anything but testing ETH provider creates a WalletSessionManager instance.
        """
        name = "anything_else"
        result = self.config_utils.create_wallet_session_manager(name)
        self.assertTrue(isinstance(result, WalletSessionManager),
                        "The wallet manager is not a WalletSessionManager")

    def test_configure_logging_no_stream(self):
        """
        Tests that logging can be configured properly without throwing exceptions.
        """
        self.config_utils.configure_logging(True, None, {})
        self.config_utils.configure_logging(False, None, {})
        args = {'log_group': 'grp', 'log_stream': 'stream', 'send_interval_seconds': 10}
        self.config_utils.configure_logging(True, "CloudWatchProvider", args)

    def test_raise_error(self):
        """
        Tests that raising an error throws an exception
        """
        self.config_utils.raise_err(False, "Message")
        try:
            self.config_utils.raise_err(True, "Message")
            self.fail("An exception was not raised")
        except ConfigurationException as e:
            # Expected
            pass

    def test_check_audit_contract_settings(self):
        """
        Tests that verification of ABI and source code in a config happens properly and admits
        exactly one of the two but not both.
        """
        both = ConfigStub(True, None, None, True, None)
        try:
            self.config_utils.check_audit_contract_settings(both)
            self.fail("Both abi and src are present but no exception was raised")
        except ConfigurationException:
            # Expected
            pass
        # Test ABI
        abi = ConfigStub(True, True, True, None, None)
        self.config_utils.check_audit_contract_settings(abi)
        abi_faulty = ConfigStub(True, False, True, None, None)
        try:
            self.config_utils.check_audit_contract_settings(abi_faulty)
            self.fail("ABI is missing configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStub(True, True, False, None, None)
        try:
            self.config_utils.check_audit_contract_settings(abi_faulty)
            self.fail("ABI is missing configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        source_faulty = ConfigStub(False, False, False, True, None)
        try:
            self.config_utils.check_audit_contract_settings(source_faulty)
            self.fail("Source is missing address but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        none = ConfigStub(False, False, False, False, False)
        try:
            self.config_utils.check_audit_contract_settings(none)
            self.fail("Neither ABi or source are present but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass

    def test_create_eth_provider_fail(self):
        """
        Tests that after failing several times, the factory raises a connection error.
        """
        # The following None makes the construction fail, keep as is!
        args = None
        try:
            self.config_utils.create_eth_provider("IPCProvider", args)
            self.fail("None parameters are provided, this should fail after several retries.")
        except ConnectionError:
            # Expected
            pass

    def test_create_eth_provider_success(self):
        """
        Tests that all providers can be successfully created and if a wrong name is specified, an
        an exception is raised.
        """
        result = self.config_utils.create_eth_provider("EthereumTesterProvider", {})
        self.assertTrue(isinstance(result, EthereumTesterProvider))
        result = self.config_utils.create_eth_provider("IPCProvider", {})
        self.assertTrue(isinstance(result, IPCProvider))
        result = self.config_utils.create_eth_provider("HTTPProvider", {})
        self.assertTrue(isinstance(result, HTTPProvider))
        result = self.config_utils.create_eth_provider("TestRPCProvider", {})
        self.assertTrue(isinstance(result, TestRPCProvider))
        try:
            self.config_utils.create_eth_provider("NonesenseProvider", {})
            self.fail("This provider does not exist, a configuration error should be raised.")
        except ConfigurationException:
            # Expected
            pass

    def test_create_web3_client(self):
        """
        Test that web3 client and accounts can be created using an ethereum provider
        """
        eth_provider = self.config_utils.create_eth_provider("EthereumTesterProvider", {})
        account = "Account"
        client, new_account = self.config_utils.create_web3_client(eth_provider, account, None)
        self.assertTrue(isinstance(client, Web3))
        self.assertEqual(account, new_account, "Account was recreated even though it was not None")
        client, new_account = self.config_utils.create_web3_client(eth_provider, None, None)
        self.assertTrue(isinstance(client, Web3))
        self.assertIsNotNone(new_account, "The account was none and was not created")

    def test_load_config(self):
        """
        Tests that utils are able to load a configuration dictionary from yaml file.
        """
        uri = resource_uri("test_config.yaml")
        config_dict = self.config_utils.load_config(uri, "local")
        self.assertIsNotNone(config_dict, "Configuration dictionary was not loaded")
        self.assertTrue("evt_db_path" in config_dict.keys(),
                        "Key evt_db_path is missing from loaded data")
