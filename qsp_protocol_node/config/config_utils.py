import config
import structlog
import utils.io as io_utils
import yaml
import os

from audit import (
    Analyzer,
    Wrapper,
)
from pathlib import Path
from tempfile import gettempdir
from streaming import CloudWatchProvider
from upload import S3Provider
from time import sleep
from web3 import (
    Web3,
    TestRPCProvider,
    HTTPProvider,
    IPCProvider,
    EthereumTesterProvider,
)


class ConfigurationException(Exception):
    """
    A specialized exception for throwing from this class.
    """


class ConfigUtils:
    """
    A utility class that helps with creating the configuration object.
    """

    def __init__(self):
        self.__logger = structlog.getLogger("config_utils")

    def create_report_uploader_provider(self, report_uploader_provider_name,
                                        report_uploader_provider_args):
        """
        Creates a report uploader provider.
        """
        # Supported providers:
        #
        # S3Provider

        if report_uploader_provider_name == "S3Provider":
            return S3Provider(**report_uploader_provider_args)

        raise ConfigurationException(
            "Unknown/Unsupported provider: {0}".format(report_uploader_provider_name))

    def create_logging_streaming_provider(self, logging_streaming_provider_name,
                                          logging_streaming_provider_args, account):
        """
        Creates a logging streaming provider.
        """
        # Supported providers:
        #
        # CloudWatchProvider

        if logging_streaming_provider_name == "CloudWatchProvider":
            return CloudWatchProvider(account, **logging_streaming_provider_args)

        raise ConfigurationException(
            "Unknown/Unsupported provider: {0}".format(logging_streaming_provider_name))

    def create_eth_provider(self, provider, args):
        if provider == "HTTPProvider":
            return HTTPProvider(**args)

        if provider == "IPCProvider":
            return IPCProvider(**args)

        if provider == "EthereumTesterProvider":
            return EthereumTesterProvider()

        if provider == "TestRPCProvider":
            return TestRPCProvider(**args)

        ConfigUtils.raise_err(True, "Unknown/Unsupported provider: {0}".format(provider))

    def create_web3_client(self, eth_provider, account, account_passwd, keystore_file, max_attempts=30):
        """
        Creates a Web3 client from the already set Ethereum provider, and creates and account.
        """
        attempts = 0

        # Default retry policy is as follows:
        # 1) Makes a query (in this case, "eth.accounts")
        # 2) If connected, nothing else to do
        # 3) Otherwise, keep trying at most max_attempts, waiting 10s per each iteration
        web3_client = Web3(eth_provider)
        new_account = account
        new_private_key = None
        connected = False
        while attempts < max_attempts and not connected:
            try:
                web3_client = Web3(eth_provider)
                # the following throws if Geth is not reachable
                _ = web3_client.eth.accounts
                connected = True
                self.__logger.debug("Connected on attempt {0}".format(attempts))
            except Exception:
                # An exception has occurred. Increment the number of attempts
                # made, and retry after 5 seconds
                attempts = attempts + 1
                self.__logger.debug(
                    "Connection attempt ({0}) failed. Retrying in 10 seconds".format(attempts))
                sleep(10)

        if not connected:
            raise ConfigurationException(
                "Could not connect to ethereum node (time out after {0} attempts).".format(
                    max_attempts
                )
            )

        # It could be the case that account is not setup, which may happen for
        # test-related providers (e.g., TestRPCProvider or EthereumTestProvider)
        if account is None:
            if len(web3_client.eth.accounts) == 0:
                raise ConfigurationException("No account was provided. Please provide an account")
            else:
                new_account = web3_client.eth.accounts[0]
                self.__logger.debug("No account was provided, using the account at index [0]",
                                    account=new_account)

        if not (keystore_file is None):
            try:
                with open(keystore_file) as keyfile:
                    encrypted_key = keyfile.read()
                    new_private_key = web3_client.eth.account.decrypt(encrypted_key, account_passwd)
            except Exception as exception:
                raise ConfigurationException("Error reading or decrypting the keystore file '{0}': {1}".format(
                    keystore_file,
                    exception)
                )

        return web3_client, new_account, new_private_key

    def configure_logging(self, logging_is_verbose, logging_streaming_provider_name,
                          logging_streaming_provider_args, account):
        if logging_is_verbose:
            config.configure_basic_logging(verbose=True)
        logger = structlog.getLogger("audit")
        logging_streaming_provider = None
        if logging_streaming_provider_name is not None:
            logging_streaming_provider = \
                self.create_logging_streaming_provider(logging_streaming_provider_name,
                                                       logging_streaming_provider_args,
                                                       account)
            logger.addHandler(logging_streaming_provider.get_handler())
        return logger, logging_streaming_provider

    def load_config(self, config_file_uri, environment):
        """
        Loads config from file and returns.
        """
        config_file_path = io_utils.fetch_file(config_file_uri)
        config_file = io_utils.load_yaml(config_file_path)
        return config_file[environment]

    def check_audit_contract_settings(self, config):
        """
        Checks the configuration values provided in the YAML configuration file.
        """
        # The contract ABI and source code are mutually exclusive, but one has to be provided.
        if config.has_audit_contract_abi:
            has_uri = bool(config.audit_contract_abi_uri)
            has_addr = bool(config.audit_contract_address)
            ConfigUtils.raise_err(not (has_uri and has_addr),
                                  "Missing audit contract ABI URI and address",
                                  )
        else:
            ConfigUtils.raise_err(msg="Missing the audit contract ABI")
        # start_n_blocks_in_the_past should never exceed the submission timeout
        ConfigUtils.raise_err(config.start_n_blocks_in_the_past > config.submission_timeout_limit_blocks)

    def create_audit_contract(self, web3_client, audit_contract_abi_uri, audit_contract_address):
        """
        Creates the audit contract either from ABI.
        """
        abi_file = io_utils.fetch_file(audit_contract_abi_uri)
        abi_json = io_utils.load_json(abi_file)

        return web3_client.eth.contract(
            address=audit_contract_address,
            abi=abi_json,
        )

    def create_analyzers(self, analyzers_config, logger):
        """
        Creates an instance of the each target analyzer that should be verifying a given contract.
        """
        default_timeout_sec = 60
        default_storage = gettempdir()
        analyzers = []

        for i, analyzer_config_dict in enumerate(analyzers_config):
            # Each analyzer config is a dictionary of a single entry
            # <analyzer_name> -> {
            #     analyzer dictionary configuration
            # }

            # Gets ths single key in the dictionart (the name of the analyzer)
            analyzer_name = list(analyzer_config_dict.keys())[0]
            analyzer_config = analyzers_config[i][analyzer_name]

            script_path = os.path.realpath(__file__)
            wrappers_dir = '{0}/../../analyzers/wrappers'.format(os.path.dirname(script_path))

            wrapper = Wrapper(
                wrappers_dir=wrappers_dir,
                analyzer_name=analyzer_name,
                args=analyzer_config.get('args', ""),
                storage_dir=analyzer_config.get('storage_dir', default_storage),
                timeout_sec=analyzer_config.get('timeout_sec', default_timeout_sec),
                logger=self.__logger,
            )

            default_storage = "{0}/.{1}".format(
                str(Path.home()),
                analyzer_name,
            )

            analyzers.append(Analyzer(wrapper, logger))

        return analyzers

    @staticmethod
    def raise_err(cond=True, msg=""):
        """
        Raises an exception if the given condition holds.
        """
        if cond:
            raise ConfigurationException("Cannot initialize QSP node. {0}".format(msg))
