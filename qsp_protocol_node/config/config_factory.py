from .config import Config


class ConfigFactory:

    @staticmethod
    def create_from_file(environment, config_file_uri, account_passwd=""):
        """
        This is now public and is to be called from wherever this class gets initialized.
        """
        config = Config()
        config.load_config(environment, config_file_uri, account_passwd)
        return config

    @staticmethod
    def create_empty_config():
        return Config()
