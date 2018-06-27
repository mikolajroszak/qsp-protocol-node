import logging
import logging.config
import structlog
import utils.io as io_utils
import yaml

from streaming import CloudWatchProvider
from upload import S3Provider
from time import sleep
from utils.eth import (
    WalletSessionManager,
    DummyWalletSessionManager,
)
from solc import compile_files
from structlog import configure_once
from structlog import processors
from structlog import stdlib
from structlog import threadlocal
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
                                          logging_streaming_provider_args):
        """
        Creates a logging streaming provider.
        """
        # Supported providers:
        #
        # CloudWatchProvider

        if logging_streaming_provider_name == "CloudWatchProvider":
            return CloudWatchProvider(**logging_streaming_provider_args)

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

    def create_wallet_session_manager(self, eth_provider_name, client=None, account=None,
                                      passwd=None):
        if eth_provider_name in ("EthereumTesterProvider", "TestRPCProvider"):
            return DummyWalletSessionManager()
        else:
            return WalletSessionManager(client, account, passwd)

    def create_web3_client(self, eth_provider, account, account_passwd, max_attempts=30):
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
        connected = False
        while attempts < max_attempts and not connected:
            try:
                web3_client = Web3(eth_provider)
                # the following throws if Geth is not reachable
                web3_client.eth.accounts
                connected = True
                self.__logger.debug("Connected on attempt {0}".format(attempts))
            except Exception:
                # An exception has occurred. Increment the number of attempts
                # made, and retry after 5 seconds
                attempts = attempts + 1
                self.__logger.debug("Connection attempt ({0}) failed. Retrying in 10 seconds".format(attempts))
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
                new_account = web3_client.personal.newAccount(account_passwd)
                self.__logger.debug("No account was provided, using a newly created one",
                                    account=new_account)
            else:
                new_account = web3_client.eth.accounts[0]
                self.__logger.debug("No account was provided, using the account at index [0]",
                                    account=new_account)
        return web3_client, new_account

    def configure_logging(self, logging_is_verbose, logging_streaming_provider_name,
                          logging_streaming_provider_args):
        # FIXME
        # This should be moved to the initialization level.
        # See QSP-148.
        # https://quantstamp.atlassian.net/browse/QSP-418
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)
        logging.getLogger('botocore').setLevel(logging.CRITICAL)

        configure_once(
            context_class=threadlocal.wrap_dict(dict),
            logger_factory=stdlib.LoggerFactory(),
            wrapper_class=stdlib.BoundLogger,
            processors=[
                stdlib.filter_by_level,
                stdlib.add_logger_name,
                stdlib.add_log_level,
                stdlib.PositionalArgumentsFormatter(),
                processors.TimeStamper(fmt="iso"),
                processors.StackInfoRenderer(),
                processors.format_exc_info,
                processors.UnicodeDecoder(),
                stdlib.render_to_log_kwargs]
        )

        dict_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    'format': '%(message)s %(threadName)s %(lineno)d %(pathname)s ',
                    'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
                }
            },
            'handlers': {
                'json': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'json'
                }
            },
            'loggers': {
                '': {
                    'handlers': ['json'],
                    'level': logging.DEBUG if logging_is_verbose else logging.INFO
                }
            }
        }

        logging.config.dictConfig(dict_config)
        logger = structlog.getLogger("audit")
        logging_streaming_provider = None
        if logging_streaming_provider_name is not None:
            logging_streaming_provider = \
                self.create_logging_streaming_provider(logging_streaming_provider_name,
                                                       logging_streaming_provider_args)
            logger.addHandler(logging_streaming_provider.get_handler())
        return logger, logging_streaming_provider

    def load_config(self, config_file_uri, environment):
        """
        Loads config from file and returns.
        """
        config_file = io_utils.fetch_file(config_file_uri)

        with open(config_file) as yaml_file:
            new_cfg_dict = yaml.load(yaml_file)[environment]
        return new_cfg_dict

    def check_audit_contract_settings(self, config):
        """
        Checks the contact configuration values provided in the YAML configuration file. The
        contract ABI and source code are mutually exclusive, but one has to be provided.
        """
        ConfigUtils.raise_err(
            config.has_audit_contract_abi and config.has_audit_contract_src,
            "Settings must include audit contract ABI or source, but not both",
        )

        if config.has_audit_contract_abi:
            has_uri = bool(config.audit_contract_abi_uri)
            has_addr = bool(config.audit_contract_address)
            ConfigUtils.raise_err(not (has_uri and has_addr),
                                  "Missing audit contract ABI URI and address",
                                  )
        elif config.has_audit_contract_src:
            has_uri = bool(config.audit_contract_src_uri)
            ConfigUtils.raise_err(not has_uri, "Missing audit contract source URI")
        else:
            ConfigUtils.raise_err(msg="Missing the audit contract source or its ABI")

    @staticmethod
    def raise_err(cond=True, msg=""):
        """
        Raises an exception if the given condition holds.
        """
        if cond:
            raise ConfigurationException("Cannot initialize QSP node. {0}".format(msg))
