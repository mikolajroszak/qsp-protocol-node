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
        cfg = { }
        expected = 1
        found = config_value(cfg, '/level1', expected)

        self.assertEqual(found, expected)  

    def test_default_in_level2_config_value(self):
        """
        Tests the retrival of an inexistent level1 configuration entry upon
        passing a default value.
        """
        cfg = { }
        expected = 1
        found = config_value(cfg, '/level1/level2', expected)

        self.assertEqual(found, expected)

    def __copy_yaml_setup(self):
        test_config = fetch_file(resource_uri('test_config.yaml'))
        with open(test_config) as yaml_file:
            cfg = yaml.load(yaml_file)

        tmp = NamedTemporaryFile(mode='w+t', delete=False) #<<<====
        yaml.dump(cfg, tmp, default_flow_style=False)

        return tmp, cfg

    def __write_yaml(self, cfg, target_file):
        target_file.seek(0, 0)
        dump = yaml.dump(cfg, default_flow_style=False)
        target_file.write(dump)
        target_file.flush()

    def test_config_reload(self):
        # Makes a copy of the test_config.yaml file to later
        # change it

        yaml_file, cfg_dict = self.__copy_yaml_setup()
        cfg = Config('test', "file://{0}".format(yaml_file.name))

        # Changes the previous settings (min_price, evt_polling, and ttl)
        # and check whether the config object is updated accordingly

        new_ttl = 1200
        new_evt_polling = 10
        new_min_price = 100

        # Updates the yaml file
        cfg_dict['test']['account']['ttl'] = new_ttl
        cfg_dict['test']['evt_polling_sec'] = new_evt_polling
        cfg_dict['test']['min_price'] = new_min_price

        # Writes the configuration back to the yaml file
        self.__write_yaml(cfg_dict, yaml_file)

        # Asserts properties have been updated
        self.assertEqual(cfg.account_ttl, new_ttl)
        self.assertEqual(cfg.evt_polling, new_evt_polling)
        self.assertEqual(cfg.min_price, new_min_price)


if __name__ == '__main__':
    unittest.main()

          




