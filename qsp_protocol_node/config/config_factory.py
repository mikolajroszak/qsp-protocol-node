from .config import Config
from .config_utils import ConfigUtils


class ConfigFactory:

    @staticmethod
    def create_from_file(environment, config_file_uri, account_passwd="", auth_token="", validate_contract_settings=True,
                         config_utils=None):
        """
        This is now public and is to be called from wherever this class gets initialized.
        """
        config = Config()
        utils = config_utils if config_utils is not None else ConfigUtils(config.node_version)
        config.load_config(utils, environment, config_file_uri, account_passwd, auth_token, validate_contract_settings)
        return config

    @staticmethod
    def create_empty_config():
        return Config()
