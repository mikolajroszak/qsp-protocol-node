####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from .config import Config
from .config_utils import ConfigUtils

# TODO Retire this code altogether in favor of module-specific factories
class ConfigFactory:

    @staticmethod
    def create_from_file(config_file_uri, environment, account_passwd="", auth_token="",
                         validate_contract_settings=True, config_utils=None):
        """
        This is now public and is to be called from wherever this class gets initialized.
        """
        config = Config()
        utils = config_utils if config_utils is not None else ConfigUtils(config.node_version)
        config.load_file(config_file_uri, utils, environment, account_passwd, auth_token,
                         validate_contract_settings)
        return config

    @staticmethod
    def create_from_dictionary(dictionary, environment, account_passwd="", auth_token="",
                               validate_contract_settings=True, config_utils=None):
        config = Config()
        utils = config_utils if config_utils is not None else ConfigUtils(config.node_version)
        config.load_dictionary(dictionary[environment], utils, environment, account_passwd,
                               auth_token, validate_contract_settings)
        return config

    @staticmethod
    def create_empty_config():
        return Config()
