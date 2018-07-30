import unittest

from audit import QSPAuditNode
from config import ConfigUtils
from config import ConfigurationException
from config import configure_basic_logging
from upload import S3Provider
from helpers.resource import resource_uri
import utils.io as io_utils
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

    def __init__(self, abi, abi_uri, contract_address,
                 submission_timeout_limit_blocks=10,
                 start_n_blocks_in_the_past=5):
        self.has_audit_contract_abi = abi
        self.audit_contract_abi_uri = abi_uri
        self.audit_contract_address = contract_address
        self.submission_timeout_limit_blocks = submission_timeout_limit_blocks
        self.start_n_blocks_in_the_past = start_n_blocks_in_the_past


class TestConfigUtil(unittest.TestCase):

    def setUp(self):
        dummy_node_version = '1.0.0'
        self.config_utils = ConfigUtils(dummy_node_version)

    def test_create_report_uploader_provider_ok(self):
        """
        Tests that the S3Provider can be created and is properly returend.
        """
        report_uploader_provider_name = "S3Provider"
        report_uploader_provider_args = {"bucket_name": "test-bucket",
                                         "contract_bucket_name": "contract_test-bucket"}
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
                                                                     streaming_provider_args,
                                                                     '0x12345')
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
                                                                streaming_provider_args,
                                                                '0x12345')
            self.fail("Succeeded to create streaming provider without proper provider name.")
        except ConfigurationException:
            # expected
            pass

    def test_configure_logging_no_stream(self):
        """
        Tests that logging can be configured properly without throwing exceptions.
        """
        account = "0x12345"
        self.config_utils.configure_logging(True, None, {}, account)
        self.config_utils.configure_logging(False, None, {}, account)
        args = {'log_group': 'grp', 'log_stream': 'stream', 'send_interval_seconds': 10}
        self.config_utils.configure_logging(True, "CloudWatchProvider", args, account)
        # this has to stay in order to disable streaming again
        configure_basic_logging()

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
        # Test ABI
        abi = ConfigStub(True, True, True)
        self.config_utils.check_audit_contract_settings(abi)
        abi_faulty = ConfigStub(True, False, True)
        try:
            self.config_utils.check_audit_contract_settings(abi_faulty)
            self.fail("ABI is missing configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStub(True, True, False)
        try:
            self.config_utils.check_audit_contract_settings(abi_faulty)
            self.fail("ABI is missing configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        none = ConfigStub(False, False, False)
        try:
            self.config_utils.check_audit_contract_settings(none)
            self.fail("Neither ABI is not present but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStub(True, True, True, 10, 20)
        try:
            self.config_utils.check_audit_contract_settings(abi_faulty)
            self.fail("ABI is missing configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass

    def test_create_eth_provider(self):
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
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, account, None, None, 2)
        self.assertTrue(isinstance(client, Web3))
        self.assertEqual(account, new_account, "Account was recreated even though it was not None")
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, None, None, None, 2)
        self.assertTrue(isinstance(client, Web3))
        self.assertIsNotNone(new_account, "The account was none and was not created")
        # None ETH provider will make this fail
        try:
            client, new_account, new_private_key = self.config_utils.create_web3_client(None, None, None, None, 2)
            self.fail("No exception was thrown even though the eth provider does not exist and web3 cannot connect")
        except ConfigurationException:
            # Expected
            pass

    def test_create_web3_client_private_key(self):
        """
        Test that private key is instantiated correctly when creating web3 client
        """
        eth_provider = self.config_utils.create_eth_provider("EthereumTesterProvider", {})
        account = "Account"
        private_key = "0xc2fd94c5216e754d3eb8f4f34017120fef318c50780ce408b54db575b120229f"
        passphrase = "abc123ropsten"
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, account, passphrase,
            io_utils.fetch_file(resource_uri("mykey.json")), 2)
        self.assertEqual(private_key, Web3.toHex(new_private_key), "Private key was not decrypted correctly")
        # None ETH provider will make this fail
        try:
            client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, account, "incorrect-passphrase",
                io_utils.fetch_file(resource_uri("mykey.json")), 2)
            self.fail("No exception was thrown even though the private key isn't correct")
        except ConfigurationException as e:
            self.assertTrue("MAC mismatch" in str(e), "Expected the MAC mismatch exception")
            # Expected
            pass

    def test_load_config(self):
        """
        Tests that utils are able to load a configuration dictionary from yaml file.
        """
        uri = resource_uri("test_config.yaml")
        config_dict = self.config_utils.load_config(uri, "local")
        self.assertIsNotNone(config_dict, "Configuration dictionary was not loaded")
        self.assertTrue("evt_db_path" in config_dict.keys(),
                        "Key evt_db_path is missing from loaded data")

    def test_create_contract(self):
        account = "Account"
        eth_provider = self.config_utils.create_eth_provider("EthereumTesterProvider", {})
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, account, None, None, 2)
        abi_uri = "file://tests/resources/QuantstampAudit.abi.json"
        address = "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"
        self.config_utils.create_audit_contract(client, abi_uri, address)

    def test_resolve_version(self):
        config_utils = ConfigUtils('10.0.1')
        version = config_utils.resolve_version('a-{major-version}-b')
        self.assertEqual(version, "a-10-b")
        version = config_utils.resolve_version('a-b')
        self.assertEqual(version, "a-b")
        version = config_utils.resolve_version(None)
        self.assertEqual(version, None)
