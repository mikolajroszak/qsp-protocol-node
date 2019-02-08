####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import utils.io as io_utils
from config import ConfigUtils
from config import ConfigurationException
from upload import S3Provider
from helpers.resource import resource_uri
from helpers.qsp_test import QSPTest
from web3 import (
    Web3,
    HTTPProvider,
    IPCProvider,
    EthereumTesterProvider,
)


class ConfigStub:
    """
    TODO(mderka): Replace this with real config class when it become available in later PRs
    """
    def __init__(self, abi, abi_uri, contract_address):
        self.has_audit_contract_abi = abi
        self.audit_contract_abi_uri = abi_uri
        self.audit_contract_address = contract_address


class AuditContractStub:

    class Function:
        def __init__(self, value):
            self.value = value

        def call(self, data):
            return self.value

    class Functions:
        def __init__(self):
            self.getAuditTimeoutInBlocks = lambda: AuditContractStub.Function(25)
            self.getMaxAssignedRequests = lambda: AuditContractStub.Function(5)

    def __init__(self):
        self.functions = AuditContractStub.Functions()


class ConfigStubForCheckSettings:
    """
    TODO: Replace this with real config class when it become available in later PRs
    Config stub for use with the check_configuration_settings function
    """

    def __init__(self,
                 start_n_blocks=1,
                 submission_timeout=1,
                 audit_timeout=5,
                 max_requests=1,
                 max_gas_price=100,
                 default_gas_price=50,
                 gas_price_strategy=None):
        self.account = "0x0"
        self.start_n_blocks_in_the_past = start_n_blocks
        self.submission_timeout_limit_blocks = submission_timeout
        self.contract_audit_timeout_in_blocks = audit_timeout
        self.max_assigned_requests = max_requests
        self.max_gas_price_wei = max_gas_price
        self.default_gas_price_wei = default_gas_price
        if not gas_price_strategy:
            gas_price_strategy = "dynamic"
        self.gas_price_strategy = gas_price_strategy
        self.audit_contract = AuditContractStub()
        self.analyzers = []


class TestConfigUtil(QSPTest):

    def setUp(self):
        dummy_node_version = '2.0.0'
        self.config_utils = ConfigUtils(dummy_node_version)

    def test_create_upload_provider_ok(self):
        """
        Tests that the S3Provider can be created and is properly returend.
        """
        upload_provider_name = "S3Provider"
        upload_provider_args = {"bucket_name": "test-bucket",
                                "contract_bucket_name": "contract_test-bucket"}
        account = "account"
        result = self.config_utils.create_upload_provider(account,
                                                          upload_provider_name,
                                                          upload_provider_args,
                                                          True)
        self.assertTrue(isinstance(result, S3Provider), "The created provider is not an S3Provider")

    def test_create_upload_provider_not_ok(self):
        """
        Tests that wrong upload provider specification causes an exception being thrown.
        """
        upload_provider_name = "nonsense"
        upload_provider_args = {}
        account = "account"
        try:
            self.config_utils.create_upload_provider(account,
                                                              upload_provider_name,
                                                              upload_provider_args,
                                                              True)
            self.fail("Succeeded to create upload provider without proper provider name.")
        except ConfigurationException:
            # expected
            pass
        try:
            self.config_utils.create_upload_provider(None, upload_provider_name, upload_provider_args, True)
            self.fail("Succeeded to create upload provider without account.")
        except ConfigurationException:
            # expected
            pass

    def test_raise_error(self):
        """
        Tests that raising an error throws an exception
        """
        self.config_utils.raise_err(False, "Message")
        try:
            self.config_utils.raise_err(True, "Message")
            self.fail("An exception was not raised")
        except ConfigurationException:
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

    def test_check_configuration_settings(self):
        """
        Tests various configuration settings
        """
        # Test ABI
        abi = ConfigStubForCheckSettings()
        self.config_utils.check_configuration_settings(abi)
        # if max_gas_price <= 0, it should be ignored
        abi = ConfigStubForCheckSettings(max_gas_price=0)
        self.config_utils.check_configuration_settings(abi)
        abi = ConfigStubForCheckSettings(gas_price_strategy="static")
        self.config_utils.check_configuration_settings(abi)
        abi_faulty = ConfigStubForCheckSettings(start_n_blocks=10)
        try:
            self.config_utils.check_configuration_settings(abi_faulty)
            self.fail("ABI has faulty configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStubForCheckSettings(submission_timeout=26)
        try:
            self.config_utils.check_configuration_settings(abi_faulty)
            self.fail("ABI has faulty configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStubForCheckSettings(max_requests=100)
        try:
            self.config_utils.check_configuration_settings(abi_faulty)
            self.fail("ABI has faulty configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStubForCheckSettings(default_gas_price=500)
        try:
            self.config_utils.check_configuration_settings(abi_faulty)
            self.fail("ABI has faulty configuration but no exception was thrown")
        except ConfigurationException:
            # Expected
            pass
        abi_faulty = ConfigStubForCheckSettings(gas_price_strategy="invalid_strategy")
        try:
            self.config_utils.check_configuration_settings(abi_faulty)
            self.fail("ABI has faulty configuration but no exception was thrown")
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
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, None, None, 2)
        self.assertTrue(isinstance(client, Web3))
        self.assertIsNotNone(new_account, "The account was none and was not created")
        # None ETH provider will make this fail
        try:
            client, new_account, new_private_key = self.config_utils.create_web3_client(None, None, None, 2)
            self.fail("No exception was thrown even though the eth provider does not exist and web3 cannot connect")
        except ConfigurationException:
            # Expected
            pass

    def test_create_web3_client_private_key(self):
        """
        Test that private key is instantiated correctly when creating web3 client
        """
        eth_provider = self.config_utils.create_eth_provider("EthereumTesterProvider", {})
        private_key = "0xc2fd94c5216e754d3eb8f4f34017120fef318c50780ce408b54db575b120229f"
        passphrase = "abc123ropsten"
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, passphrase,
            io_utils.fetch_file(resource_uri("mykey.json")), 2)
        self.assertEqual(private_key, Web3.toHex(new_private_key), "Private key was not decrypted correctly")
        # None ETH provider will make this fail
        try:
            client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, "incorrect-passphrase",
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
        config_dict = self.config_utils.load_config(uri, "dev")
        self.assertIsNotNone(config_dict, "Configuration dictionary was not loaded")
        self.assertTrue("evt_db_path" in config_dict.keys(),
                        "Key evt_db_path is missing from loaded data")

    def test_create_contract(self):
        eth_provider = self.config_utils.create_eth_provider("EthereumTesterProvider", {})
        client, new_account, new_private_key = self.config_utils.create_web3_client(eth_provider, None, None, 2)
        abi_uri = "file://tests/resources/QuantstampAudit.abi.json"
        address = "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"
        self.config_utils.create_contract(client, abi_uri, address)

    def test_resolve_version(self):
        config_utils = ConfigUtils('10.0.1')
        version = config_utils.resolve_version('a-{major-version}-b')
        self.assertEqual(version, "a-10-b")
        version = config_utils.resolve_version('a-b')
        self.assertEqual(version, "a-b")
        version = config_utils.resolve_version(None)
        self.assertEqual(version, None)
