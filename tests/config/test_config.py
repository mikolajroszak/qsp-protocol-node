"""
Tests different scenarios for retrieving configuration values.
"""
import unittest
import yaml
from dpath.util import get
from tempfile import NamedTemporaryFile
from config import config_value, Config
from helpers.resource import resource_uri
from utils.io import fetch_file


class FunctionCall:

    def __init__(self, function_name, params, return_value):
        self.params = params
        self.function_name = function_name
        self.return_value = return_value

    def __str__(self):
        return self.function_name

    def __repr__(self):
        return self.function_name


class ConfigUtilsMock:
    """
    A mock class used as stub for the internals of the Web3 provider.
    """

    def __init__(self):
        self.expected = []

    def expect(self, function, params, return_value):
        """
        Adds an expected function call to the queue.
        """
        self.expected.append(FunctionCall(function, params, return_value))

    def verify(self):
        """
        Verifies that all the expected calls were performed.
        """
        if len(self.expected) != 0:
            raise Exception('Some excpected calls were left over: ' + str(self.expected))

    def call(self, function_name, arguments_to_check, local_values):
        """
        Simulates call to the specified function while checking the expected parameter values
        """
        first_call = self.expected[0]
        if first_call.function_name != function_name:
            raise Exception('{0} call expected'.format(function_name))
        for argument in arguments_to_check:
            if first_call.params[argument] != local_values[argument]:
                msg = 'Value of {0} is not {1} as expected but {2}'
                raise Exception(msg.format(argument, first_call.params[argument], local_values[argument]))
        self.expected = self.expected[1:]
        return first_call.return_value

    def create_wallet_session_manager(self, eth_provider_name, client=None, account=None, passwd=None):
        """
        A stub for the create_wallet_session_manager method.
        """
        arguments_to_check = ['eth_provider_name', 'client', 'account', 'passwd']
        return self.call('create_wallet_session_manager', arguments_to_check, locals())

    def create_report_uploader_provider(self, report_uploader_provider_name, report_uploader_provider_args):
        """
        A stub for the report_uploader_provider method.
        """
        arguments_to_check = ['report_uploader_provider_name', 'report_uploader_provider_args']
        return self.call('create_report_uploader_provider', arguments_to_check, locals())

    def new_provider(self, provider, args):
        """
        A stub for new_provider method.
        """
        arguments_to_check = ['provider', 'args']
        return self.call('new_provider', arguments_to_check, locals())


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

        tmp = NamedTemporaryFile(mode='w+t', delete=False)  # <<<====
        yaml.dump(cfg, tmp, default_flow_style=False)

        return tmp, cfg

    def __write_yaml(self, cfg, target_file):
        target_file.seek(0, 0)
        dump = yaml.dump(cfg, default_flow_style=False)
        target_file.write(dump)
        target_file.flush()

    @staticmethod
    def fetch_config():
        config_file_uri = resource_uri("test_config.yaml")
        return Config("local", config_file_uri)

    def test_create_wallet_session_manager(self):
        account = "some account"
        passwd = "some passwd"
        web3_client = "some client"
        provider = "some name"
        return_value = "value"
        config = TestConfig.fetch_config()
        config._Config__eth_provider_name = provider
        config._Config__account = account
        config._Config__web3_client = web3_client
        config._Config__account_passwd = passwd
        utils = ConfigUtilsMock()
        utils.expect('create_wallet_session_manager',
                     {'eth_provider_name': provider, 'client': web3_client, 'account': account, 'passwd': passwd},
                     return_value)
        result = config._Config__create_wallet_session_manager(utils)
        self.assertEqual(return_value, result)
        utils.verify()

    def test_create_report_uploader_provider(self):
        name = "provider name"
        args = "arguments"
        return_value = "value"
        config = TestConfig.fetch_config()
        config._Config__report_uploader_provider_name = name
        config._Config__report_uploader_provider_args = args
        utils = ConfigUtilsMock()
        utils.expect('create_report_uploader_provider',
                     {'report_uploader_provider_name': name, 'report_uploader_provider_args': args},
                     return_value)
        result = config._Config__create_report_uploader_provider(utils)
        self.assertEqual(return_value, result)
        utils.verify()

    def test_create_eth_provider(self):
        name = "provider name"
        args = "arguments"
        return_value = "value"
        config = TestConfig.fetch_config()
        config._Config__eth_provider_name = name
        config._Config__eth_provider_args = args
        utils = ConfigUtilsMock()
        utils.expect('new_provider',
                     {'provider': name, 'args': args},
                     return_value)
        result = config._Config__create_eth_provider(utils)
        self.assertEqual(return_value, result)
        utils.verify()


#    def test_config_reload(self):
#        # Makes a copy of the test_config.yaml file to later
#        # change it
#
#        yaml_file, cfg_dict = self.__copy_yaml_setup()
#        cfg = Config('test', "file://{0}".format(yaml_file.name))
#
#        # Changes the previous settings (min_price, evt_polling, and ttl)
#        # and check whether the config object is updated accordingly
#
#        new_ttl = 1200
#        new_evt_polling = 10
#        new_min_price = 100
#
#        # Updates the yaml file
#        cfg_dict['test']['account']['ttl'] = new_ttl
#        cfg_dict['test']['evt_polling_sec'] = new_evt_polling
#        cfg_dict['test']['min_price'] = new_min_price
#
#        # Writes the configuration back to the yaml file
#        self.__write_yaml(cfg_dict, yaml_file)
#
#        # Asserts properties have been updated
#        self.assertEqual(cfg.account_ttl, new_ttl)
#        self.assertEqual(cfg.evt_polling, new_evt_polling)
#        self.assertEqual(cfg.min_price, new_min_price)


if __name__ == '__main__':
    unittest.main()
