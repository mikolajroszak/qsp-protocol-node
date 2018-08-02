"""
Tests different scenarios for retrieving configuration values.
"""
import unittest
import yaml

from tempfile import NamedTemporaryFile
from config import config_value, Config, ConfigFactory
from helpers.simple_mock import SimpleMock
from helpers.resource import resource_uri
from utils.io import (
    fetch_file,
    load_yaml,
)
from unittest.mock import Mock


class ConfigUtilsDummy:
    def __init__(self, return_values):
        self.return_values = return_values

    def create_report_uploader_provider(self, account, report_uploader_provider_name, report_uploader_provider_args):
        return self.return_values.get('create_report_uploader_provider', None)

    def create_eth_provider(self, provider, args):
        return self.return_values.get('create_eth_provider', None)

    def configure_logging(self, logging_is_verbose, logging_streaming_provider_name,
                    logging_streaming_provider_args, account):
        return self.return_values.get('configure_logging', (Mock(), None))

    def create_analyzers(self, analyzers_config, logger):
        return self.return_values.get('create_analyzers', None)

    def check_audit_contract_settings(self):
        return self.return_values.get('check_audit_contract_settings', None)

    def create_audit_contract(self, web3_client, audit_contract_abi_uri, audit_contract_address):
        return self.return_values.get('create_audit_contract', None)

    def create_web3_client(self, eth_provider, account, account_passwd, keystore_file, max_attempts=30):
        return self.return_values.get('create_web3_client', (None, None, None))

    def load_config(self, config_file_uri, environment):
        return self.return_values.get('load_config', None)

    def resolve_version(self, input):
        return self.return_values.get('resolve_version', None)


class ConfigUtilsMock(SimpleMock):
    """
    A mock class used as stub for the internals of the Web3 provider.
    """

    def create_report_uploader_provider(self, account, report_uploader_provider_name,
                                        report_uploader_provider_args):
        """
        A stub for the report_uploader_provider method.
        """
        arguments_to_check = ['account', 'report_uploader_provider_name',
                              'report_uploader_provider_args']
        return self.call('create_report_uploader_provider', arguments_to_check, locals())

    def create_eth_provider(self, provider, args):
        """
        A stub for new_provider method.
        """
        arguments_to_check = ['provider', 'args']
        return self.call('create_eth_provider', arguments_to_check, locals())

    def configure_logging(self, logging_is_verbose, logging_streaming_provider_name,
                          logging_streaming_provider_args, account):
        """
        A stub for configure_logging method.
        """
        arguments_to_check = ['logging_is_verbose', 'logging_streaming_provider_name',
                              'logging_streaming_provider_args', 'account']
        return self.call('configure_logging', arguments_to_check, locals())

    def create_analyzers(self, analyzers_config, logger):
        """
        A stub for configure_logging method.
        """
        arguments_to_check = ['analyzers_config', 'logger']
        return self.call('create_analyzers', arguments_to_check, locals())

    def check_audit_contract_settings(self, config):
        """
        A stub for configure_logging method.
        """
        arguments_to_check = ['config']
        return self.call('check_audit_contract_settings', arguments_to_check, locals())

    def create_audit_contract(self, web3_client, audit_contract_abi_uri, audit_contract_address):
        arguments_to_check = ['web3_client', 'audit_contract_abi_uri', 'audit_contract_address']
        return self.call('create_audit_contract', arguments_to_check, locals())

    def create_web3_client(self, eth_provider, account, account_passwd, keystore_file, max_attempts=30):
        arguments_to_check = ['eth_provider', 'account', 'account_passwd', 'keystore_file', 'max_attempts']
        return self.call('create_web3_client', arguments_to_check, locals())


class Web3Mock:

    def isAddress(self, address):
        return address == "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"

    def isChecksumAddress(self, address):
        return address == "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"


class TestConfig(unittest.TestCase):
    """
    Asserts different properties of Config objects.
    """

    def test_existent_level1_config_value(self):
        """
        Tests the retrival of an existent level1 configuration entry.
        """
        cfg = {
            'level1': 1
        }
        expected = 1
        found = config_value(cfg, '/level1')

        self.assertEqual(found, expected)

    def test_existent_level2_config_value(self):
        """
        Tests the retrival of an existent level2 configuration entry.
        """
        cfg = {
            'level1': {
                'level2': 1
            }
        }
        expected = 1
        found = config_value(cfg, '/level1/level2')

        self.assertEqual(found, expected)

    def test_inexistent_level1_config_value(self):
        """
        Tests the retrival of an inexistent level1 configuration entry.
        """
        cfg = {
            'level1': {
                'level2': 1
            }
        }

        with self.assertRaises(Exception):
            config_value(cfg, '/inexistent', accept_none=False)

    def test_inexistent_level2_config_value(self):
        """
        Tests the retrival of an inexistent level2 configuration entry.
        """
        cfg = {
            'level1': {
                'level2': 1
            }
        }

        with self.assertRaises(Exception):
            config_value(cfg, '/level1/inexistent', accept_none=False)

    def test_default_in_level1_config_value(self):
        """
        Tests the retrival of an inexistent level1 configuration entry upon
        passing a default value.
        """
        cfg = {}
        expected = 1
        found = config_value(cfg, '/level1', expected)

        self.assertEqual(found, expected)

    def test_default_in_level2_config_value(self):
        """
        Tests the retrival of an inexistent level1 configuration entry upon
        passing a default value.
        """
        cfg = {}
        expected = 1
        found = config_value(cfg, '/level1/level2', expected)

        self.assertEqual(found, expected)

    def __copy_yaml_setup(self):
        test_config = fetch_file(resource_uri('test_config.yaml'))
        with open(test_config) as yaml_file:
            cfg = yaml.load(yaml_file)

        tmp = NamedTemporaryFile(mode='w+t', delete=False)
        yaml.dump(cfg, tmp, default_flow_style=False)

        return tmp, cfg

    def __write_yaml(self, cfg, target_file):
        target_file.seek(0, 0)
        dump = yaml.dump(cfg, default_flow_style=False)
        target_file.write(dump)
        target_file.flush()

    def test_create_report_uploader_provider(self):
        account = "account"
        report_uploader_provider_name = "provider name"
        report_uploader_provider_args = "arguments"
        report_uploader = "value"
        config = ConfigFactory.create_empty_config()
        config._Config__account = account
        config._Config__report_uploader_provider_name = report_uploader_provider_name
        config._Config__report_uploader_provider_args = report_uploader_provider_args
        utils = ConfigUtilsMock()
        utils.expect('create_report_uploader_provider',
                     {'account': account,
                      'report_uploader_provider_name': report_uploader_provider_name,
                      'report_uploader_provider_args': report_uploader_provider_args},
                     report_uploader)
        result = config._Config__create_report_uploader_provider(utils)
        self.assertEqual(report_uploader, result)
        utils.verify()

    def test_create_eth_provider(self):
        name = "provider name"
        args = "arguments"
        return_value = "value"
        config = ConfigFactory.create_empty_config()
        config._Config__eth_provider_name = name
        config._Config__eth_provider_args = args
        utils = ConfigUtilsMock()
        utils.expect('create_eth_provider',
                     {'provider': name, 'args': args},
                     return_value)
        result = config._Config__create_eth_provider(utils)
        self.assertEqual(return_value, result)
        utils.verify()

    def test_configure_logging(self):
        name = "provider name"
        args = "arguments"
        return_value = "value"
        verbose = False
        account = "0x12345"
        config = ConfigFactory.create_empty_config()
        config._Config__logging_is_verbose = verbose
        config._Config__logging_streaming_provider_name = name
        config._Config__logging_streaming_provider_args = args
        config._Config__account = account
        utils = ConfigUtilsMock()
        utils.expect('configure_logging',
                     {'logging_is_verbose': verbose, 'logging_streaming_provider_name': name,
                      'logging_streaming_provider_args': args, 'account': account},
                     return_value)
        result = config._Config__configure_logging(utils)
        self.assertEqual(return_value, result)
        utils.verify()

    def test_create_analyzers(self):
        analyzers_config = "config list"
        logger = "logger"
        return_value = "value"
        config = ConfigFactory.create_empty_config()
        config._Config__analyzers_config = analyzers_config
        config._Config__logger = logger
        utils = ConfigUtilsMock()
        utils.expect('create_analyzers',
                     {'analyzers_config': analyzers_config, 'logger': logger},
                     return_value)
        result = config._Config__create_analyzers(utils)
        self.assertEqual(return_value, result)
        utils.verify()

    def test_create_web3_client(self):
        eth_provider = "eth_provider"
        account = "account"
        account_passwd = "account password"
        account_keystore_file = "./mykey.json"
        created_web3_provider = "created provider"
        config = ConfigFactory.create_empty_config()
        config._Config__eth_provider = eth_provider
        config._Config__account = account
        config._Config__account_passwd = account_passwd
        config._Config__account_keystore_file = account_keystore_file
        utils = ConfigUtilsMock()
        utils.expect('create_web3_client',
                     {'eth_provider': eth_provider, 'account': account, 'account_passwd': account_passwd,
                      'keystore_file': account_keystore_file, 'max_attempts': 30},
                     created_web3_provider)
        result = config._Config__create_web3_client(utils)
        self.assertEqual(created_web3_provider, result)
        utils.verify()

    def test_constructor(self):
        """
        Tests that all properties are listed in the constructor and have default values
        """
        config = Config()
        self.assertIsNone(config.eth_provider)
        self.assertIsNone(config.eth_provider_name)
        self.assertIsNone(config.eth_provider_args)
        self.assertIsNone(config.audit_contract_address)
        self.assertEqual(0, config.min_price)
        self.assertEqual(0, config.evt_polling)
        self.assertIsNone(config.report_uploader)
        self.assertIsNone(config.account)
        self.assertIsNone(config.account_passwd)
        self.assertIsNone(config.account_keystore_file)
        self.assertIsNone(config.account_private_key)
        self.assertIsNone(config.audit_contract_abi_uri)
        self.assertFalse(config.has_audit_contract_abi)
        self.assertIsNone(config.web3_client)
        self.assertIsNone(config.audit_contract)
        self.assertIsNone(config.audit_contract_name)
        self.assertEqual(0, len(config.analyzers))
        self.assertEqual(0, config.gas)
        self.assertIsNone(config.env)
        self.assertEqual(0, config.gas_price_wei)
        self.assertIsNone(config.config_file_uri)
        self.assertIsNone(config.evt_db_path)
        self.assertEqual(10, config.submission_timeout_limit_blocks)
        self.assertIsNone(config.event_pool_manager)
        self.assertIsNone(config.logger)
        self.assertTrue(config.metric_collection_is_enabled)
        self.assertEquals(30, config.metric_collection_interval_seconds)
        self.assertIsNone(config.logging_streaming_provider)
        self.assertIsNone(config.report_uploader_provider_name)
        self.assertIsNone(config.report_uploader_provider_args)
        self.assertEqual(0, len(config.analyzers_config))
        self.assertFalse(config.logging_is_verbose)
        self.assertIsNone(config.logging_streaming_provider_name)
        self.assertIsNone(config.logging_streaming_provider_args)
        self.assertEqual(0, config.start_n_blocks_in_the_past)
        self.assertEqual(0, config.block_discard_on_restart)

    def test_create_components(self):
        logging_provider_name = "provider name"
        logging_provider_args = "arguments"
        logger = "created logger"
        streaming_provider = "created streaming provider"
        verbose = False
        eth_provider_name = "eth provider name"
        eth_provider_args = "eth provider arguments"
        created_eth_provider = "created_eth_provider"
        new_account = "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"
        account_passwd = "account password"
        account_keystore_file = "./mykey.json"
        new_private_key = "abcdefg"
        account = "0x12345"
        analyzers_config = "config list"
        created_analyzers = "analyzers"
        report_uploader_provider_name = "uploader provider name"
        report_uploader_provider_args = "uploadervarguments"
        report_uploader = "created report uploader"
        audit_contract_abi_uri = "some uri"
        audit_contract_address = "0xc1220b0bA0760817A9E8166C114D3eb2741F5949"
        created_audit_contract = "contract"
        created_web3_client = Web3Mock()
        config = ConfigFactory.create_empty_config()
        config._Config__logging_is_verbose = verbose
        config._Config__logging_streaming_provider_name = logging_provider_name
        config._Config__logging_streaming_provider_args = logging_provider_args
        config._Config__eth_provider_name = eth_provider_name
        config._Config__eth_provider_args = eth_provider_args
        config._Config__account = account
        config._Config__account_passwd = account_passwd
        config._Config__account_keystore_file = account_keystore_file
        config._Config__analyzers_config = analyzers_config
        config._Config__evt_db_path = "/tmp/evts.test"
        config._Config__report_uploader_provider_name = report_uploader_provider_name
        config._Config__report_uploader_provider_args = report_uploader_provider_args
        config._Config__audit_contract_abi_uri = audit_contract_abi_uri
        config._Config__audit_contract_address = audit_contract_address
        utils = ConfigUtilsMock()
        utils.expect('configure_logging',
                     {'logging_is_verbose': verbose, 'logging_streaming_provider_name': logging_provider_name,
                      'logging_streaming_provider_args': logging_provider_args, 'account': account},
                     (logger, streaming_provider))
        utils.expect('check_audit_contract_settings',
                     {'config': config},
                     None)
        utils.expect('create_eth_provider',
                     {'provider': eth_provider_name, 'args': eth_provider_args},
                     created_eth_provider)
        utils.expect('create_web3_client',
                     {'eth_provider': created_eth_provider, 'account': account, 'account_passwd': account_passwd,
                      'keystore_file': account_keystore_file, 'max_attempts': 30},
                     (created_web3_client, new_account, new_private_key))
        utils.expect('create_audit_contract',
                     {'web3_client': created_web3_client, 'audit_contract_abi_uri': audit_contract_abi_uri,
                      'audit_contract_address': audit_contract_address},
                     created_audit_contract)
        utils.expect('create_analyzers',
                     {'analyzers_config': analyzers_config, 'logger': logger},
                     created_analyzers)
        utils.expect('create_report_uploader_provider',
                     {'account': new_account,
                      'report_uploader_provider_name': report_uploader_provider_name,
                      'report_uploader_provider_args': report_uploader_provider_args},
                     report_uploader)
        config._Config__create_components(utils)
        self.assertEqual(logger, config.logger)
        self.assertEqual(streaming_provider, config.logging_streaming_provider)
        self.assertEqual(created_eth_provider, config.eth_provider)
        self.assertEqual(created_web3_client, config.web3_client)
        self.assertEqual(new_account, config.account)
        self.assertEqual(created_analyzers, config.analyzers)
        self.assertEqual(report_uploader, config.report_uploader)
        self.assertEqual(created_audit_contract, config.audit_contract)
        utils.verify()

    def test_load_config(self):
        config_file_uri = resource_uri("test_config.yaml")
        config = ConfigFactory.create_from_file("local", config_file_uri, validate_contract_settings=False)
        self.assertIsNotNone(config.logger)
        self.assertIsNone(config.logging_streaming_provider)
        self.assertIsNotNone(config.eth_provider)
        self.assertIsNotNone(config.web3_client)
        self.assertIsNotNone(config.account)
        self.assertIsNotNone(config.analyzers)
        self.assertIsNotNone(config.report_uploader)
        self.assertEqual(0, config.min_price)
        self.assertEqual(0, config.gas_price_wei)
        self.assertEqual(5, config.evt_polling)
        self.assertEqual(2, len(config.analyzers))
        self.assertEqual(25, config.start_n_blocks_in_the_past)
        self.assertEqual(1, config.block_discard_on_restart)

    def test_inject_token_auth(self):
        auth_token = "abc123456"
        endpoint = "https://test.com/?token={0}".format(auth_token)
        target_env = "local"

        # Sets the dictionary to be returned by a call to load_config
        config_file = fetch_file(resource_uri("test_config_with_auth_token.yaml"))
        config_yaml = load_yaml(config_file)
        dummy_utils = ConfigUtilsDummy({'load_config': config_yaml[target_env]})

        config = ConfigFactory.create_from_file(
            environment=target_env,
            config_file_uri="some dummy uri",
            auth_token=auth_token,
            validate_contract_settings=False,
            config_utils=dummy_utils,
        )
        self.assertEqual(config.auth_token, auth_token)
        self.assertEqual(config.eth_provider_args['endpoint_uri'], endpoint)


if __name__ == '__main__':
    unittest.main()
