####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from .config import Config
from .config_utils import ConfigUtils


class ConfigFactory:

    @staticmethod
    def create_from_file(config_file_uri, environment, node_version, qsp_home_dir, account_passwd="",
                         validate_contract_settings=True, config_utils=None):
        """
        This is now public and is to be called from wherever this class gets initialized.
        """
        config = Config(node_version)
        utils = config_utils if config_utils is not None else ConfigUtils()
        config.load_file(config_file_uri, utils, environment, account_passwd,
                         validate_contract_settings)
        return config

    @staticmethod
    def create_from_dictionary(dictionary, environment, node_version, qsp_home_dir, account_passwd="", 
                               validate_contract_settings=True, config_utils=None):
        config = Config(node_version)
        utils = config_utils if config_utils is not None else ConfigUtils()
        config.load_dictionary(dictionary[environment], utils, environment, account_passwd,
                               validate_contract_settings)
        return config

    @staticmethod
    def create_empty_config(node_version):
        return Config(node_version)
