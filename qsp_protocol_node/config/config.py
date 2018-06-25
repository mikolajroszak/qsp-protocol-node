"""
Provides the configuration for executing a QSP Audit node,
as loaded from an input YAML file.
"""
import logging
import logging.config
import os
import structlog
import utils.io as io_utils
import yaml

from audit import (
    Analyzer,
    Wrapper,
)
from evt import EventPoolManager
from dpath.util import get
from os.path import expanduser
from pathlib import Path
from solc import compile_files
from streaming import CloudWatchProvider
from structlog import configure_once
from structlog import processors
from structlog import stdlib
from structlog import threadlocal
from time import sleep
from tempfile import gettempdir
from upload import S3Provider
from utils.eth import (
    WalletSessionManager,
    DummyWalletSessionManager,
    mk_checksum_address,
)
from web3 import (
    Web3,
    TestRPCProvider,
    HTTPProvider,
    IPCProvider,
    EthereumTesterProvider,
)


def config_value(cfg, path, default=None, accept_none=True):
    """
    Extracts a configuration entry from a given configuration dictionary.
    """
    try:
        value = get(cfg, path)
    except KeyError as key_error:
        if default is not None:
            return default

        if accept_none:
            return None

        raise key_error

    return value


# FIXME
# There is some technical debt accumulating in this file. Config started simple and therefore justified
# its own existence as a self-contained module. This has to change as we move forward. Break config
# into smaller subconfigs. See QSP-414.
# https://quantstamp.atlassian.net/browse/QSP-414

class Config:
    """
    Provides a set of methods for accessing configuration parameters.
    """

    def __fetch_audit_contract_metadata(self, cfg):
        metadata_uri = config_value(cfg, '/audit_contract_abi/metadata')
        if metadata_uri is not None:
            return io_utils.load_json(
                io_utils.fetch_file(metadata_uri)
            )

        metadata_uri = config_value(cfg, '/audit_contract_src/metadata')
        if metadata_uri is not None:
            return io_utils.load_json(
                io_utils.fetch_file(metadata_uri)
            )

        raise Exception("Missing audit contract metadata")

    def __setup_values(self, cfg):
        audit_contract_metadata = self.__fetch_audit_contract_metadata(cfg)
        self.__audit_contract_name = config_value(
            audit_contract_metadata,
            '/contractName',
        )
        self.__audit_contract_address = config_value(
            audit_contract_metadata,
            '/contractAddress',
        )
        self.__audit_contract = None

        self.__audit_contract_src_uri = config_value(
            cfg,
            '/audit_contract_src/uri',
        )
        self.__has_audit_contract_src = bool(
            self.__audit_contract_src_uri
        )
        self.__audit_contract_abi_uri = config_value(
            cfg,
            '/audit_contract_abi/uri',
        )
        self.__has_audit_contract_abi = bool(
            self.__audit_contract_abi_uri
        )
        self.__eth_provider_name = config_value(
            cfg,
            '/eth_node/provider',
            accept_none=False,
        )
        self.__eth_provider = None
        self.__eth_provider_args = config_value(
            cfg,
            '/eth_node/args',
            {},
        )
        self.__min_price = config_value(
            cfg,
            '/min_price',
            accept_none=False,
        )
        self.__evt_polling_sec = config_value(
            cfg,
            '/evt_polling_sec',
            accept_none=False,
        )
        self.__analyzers = []
        self.__analyzers_config = config_value(
            cfg,
            '/analyzers',
            accept_none=False,
        )
        self.__account = config_value(
            cfg,
            '/account/id',
        )
        self.__account_ttl = config_value(
            cfg,
            '/account/ttl',
            600,
        )
        self.__default_gas = config_value(
            cfg,
            '/default_gas'
        )
        self.__evt_db_path = config_value(
            cfg,
            '/evt_db_path',
            expanduser("~") + "/" + ".audit_node.db",
        )
        self.__submission_timeout_limit_blocks = config_value(
            cfg,
            '/submission_timeout_limit_blocks',
            10,
        )
        self.__default_gas = config_value(
            cfg,
            '/default_gas',
        )
        self.__report_uploader_provider_name = config_value(
            cfg,
            '/report_uploader/provider',
        )
        self.__report_uploader_provider_args = config_value(
            cfg,
            '/report_uploader/args',
            {}
        )
        self.__logging_is_verbose = config_value(
            cfg,
            '/logging/is_verbose',
            False
        )
        self.__logging_streaming_provider_name = config_value(
            cfg,
            '/logging/streaming/provider',
        )
        self.__logging_streaming_provider_args = config_value(
            cfg,
            '/logging/streaming/args',
            {}
        )
        self.__metric_collection_is_enabled = config_value(
            cfg,
            '/metric_collection/is_enabled',
            False
        )
        self.__metric_collection_interval_seconds = config_value(
            cfg,
            '/metric_collection/interval_seconds',
            30
        )

    def __check_values(self):
        """
        Checks the configuration values provided in the YAML configuration file.
        """
        self.__check_audit_contract_settings()

    def __check_audit_contract_settings(self):
        """
        Checks the settings w.r.t. the audit contract.
        """
        self.__raise_err(
            self.__has_audit_contract_abi and self.__has_audit_contract_src,
            "Settings must include audit contract ABI or source, but not both",
        )

        if self.__has_audit_contract_abi:
            has_uri = bool(self.__audit_contract_abi_uri)
            has_addr = bool(self.__audit_contract_address)
            self.__raise_err(
                not (has_uri and has_addr),
                "Missing audit contract ABI URI and address",
            )

        elif self.__has_audit_contract_src:
            has_uri = bool(self.__audit_contract_src_uri)
            self.__raise_err(
                not has_uri,
                "Missing audit contract source URI"
            )
        else:
            self.__raise_err(
                msg="Missing the audit contract source or its ABI")

    @staticmethod
    def __new_provider(provider, args):
        if provider == "HTTPProvider":
            return HTTPProvider(**args)

        if provider == "IPCProvider":
            return IPCProvider(**args)

        if provider == "EthereumTesterProvider":
            return EthereumTesterProvider()

        if provider == "TestRPCProvider":
            return TestRPCProvider(**args)

        raise Exception(
            "Unknown/Unsupported provider: {0}".format(provider)
        )

    def __create_eth_provider(self):
        """
        Creates an Ethereum provider.
        """
        # Known providers according to Web3
        #
        # HTTPProvider
        # IPCProvider
        # EthereumTesterProvider
        # TestRPCProvider
        #
        # See: http://web3py.readthedocs.io/en/stable/providers.html

        max_attempts = 6
        attempts = 0

        # Default policy for creating a provider is as follows:
        # 1) Creates a given provider and checks if it is connected or not
        # 2) If connected, nothing else to do
        # 3) Otherwise, keep trying at most max_attempts, waiting 5s per each iteration

        self.__eth_provider = None
        connected = False

        while attempts < max_attempts and not connected:
            try:
                self.__eth_provider = Config.__new_provider(self.__eth_provider_name,
                                                            self.__eth_provider_args)
                connected = True
            except Exception:
                # An exception has occurred. Increment the number of attempts
                # made, and retry after 5 seconds
                attempts = attempts + 1
                self.__logger.debug("Connection attempt ({0}) failed. Retrying in 5 seconds".format(
                    attempts
                    )
                )
                sleep(5)

        if not connected:
            self.__eth_provider = None
            raise Exception(
                "Could not connect to ethereum node (time out after {0} attempts).".format(
                    max_attempts
                )
            )

    def __create_report_uploader_provider(self):
        """
        Creates a report uploader provider.
        """
        # Supported providers:
        #
        # S3Provider

        if self.__report_uploader_provider_name == "S3Provider":
            self.__report_uploader = S3Provider(**self.__report_uploader_provider_args)
            return

        raise Exception(
            "Unknown/Unsupported provider: {0}".format(self.__report_uploader_provider_name))

    def __create_logging_streaming_provider(self):
        """
        Creates a logging streaming provider.
        """
        # Supported providers:
        #
        # CloudWatchProvider

        if self.__logging_streaming_provider_name == "CloudWatchProvider":
            self.__logging_streaming_provider = CloudWatchProvider(
                **self.__logging_streaming_provider_args)
            return

        raise Exception(
            "Unknown/Unsupported provider: {0}".format(self.__logging_streaming_provider_name))

    def __create_web3_client(self):
        """
        Creates a Web3 client from the already set Ethereum provider.
        """
        self.__web3_client = Web3(self.eth_provider)

        # It could be the case that account is not setup, which may happen for
        # test-related providers (e.g., TestRPCProvider or EthereumTestProvider)
        if self.__account is None:
            if len(self.__web3_client.eth.accounts) == 0:
                self.__account = self.__web3_client.personal.newAccount(self.__account_passwd)
                self.__logger.debug("No account was provided, using a newly created one",
                                    account=self.__account)
            else:
                self.__account = self.__web3_client.eth.accounts[0]
                self.__logger.debug("No account was provided, using the account at index [0]",
                                    account=self.__account)

    def __load_audit_contract_from_src(self, contract_src_uri, contract_name, constructor_from):
        """
        Loads the QuantstampAuditMock contract from source code (useful for testing purposes),
        returning the (address, contract) pair.
        """
        audit_contract_src = io_utils.fetch_file(contract_src_uri)
        contract_dict = compile_files([audit_contract_src])
        contract_id = "{0}:{1}".format(
            contract_src_uri,
            contract_name,
        )
        contract_interface = contract_dict[contract_id]

        # deploy the audit contract
        contract = self.web3_client.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )
        tx_hash = contract.constructor().transact({'from': constructor_from, 'gasPrice': 0})
        receipt = self.web3_client.eth.getTransactionReceipt(tx_hash)
        address = receipt['contractAddress']
        contract = self.web3_client.eth.contract(
            abi=contract_interface['abi'],
            address=address,
        )
        return address, contract

    def __create_audit_contract(self):
        """
        Creates the audit contract either from its ABI or from its source code (whichever is
        available).
        """
        self.__audit_contract = None

        if self.__has_audit_contract_abi:
            # Creates contract from ABI settings

            abi_file = io_utils.fetch_file(self.audit_contract_abi_uri)
            abi_json = io_utils.load_json(abi_file)

            self.__audit_contract = self.web3_client.eth.contract(
                address=self.audit_contract_address,
                abi=abi_json,
            )

        else:
            self.__audit_contract_address, self.__audit_contract = \
                self.__load_audit_contract_from_src(
                    self.__audit_contract_src_uri,
                    self.__audit_contract_name,
                    self.__account)

    def __create_analyzers(self):
        """
        Creates an instance of the each target analyzer that should be verifying a given contract.
        """
        default_timeout_sec = 60
        default_storage = gettempdir()

        for i, analyzer_config_dict in enumerate(self.__analyzers_config):
            # Each analyzer config is a dictionary of a single entry
            # <analyzer_name> -> {
            #     analyzer dictionary configuration
            # }

            # Gets ths single key in the dictionart (the name of the analyzer)
            analyzer_name = list(analyzer_config_dict.keys())[0]
            analyzer_config = self.__analyzers_config[i][analyzer_name]

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

            self.__analyzers.append(Analyzer(wrapper, self.__logger))

    def __create_wallet_session_manager(self):
        if self.eth_provider_name in ("EthereumTesterProvider", "TestRPCProvider"):
            self.__wallet_session_manager = DummyWalletSessionManager()
        else:
            self.__wallet_session_manager = WalletSessionManager(
                self.__web3_client, self.__account, self.__account_passwd)

    def __create_event_pool_manager(self):
        self.__event_pool_manager = EventPoolManager(self.evt_db_path, self.__logger)

    def __create_components(self, cfg):
        # Setup followed by verification
        self.__setup_values(cfg)
        self.__configure_logging()
        self.__check_values()

        # Creation of internal components
        self.__create_eth_provider()
        self.__create_web3_client()

        # After having a web3 client object, use it to put addresses in a canonical format
        self.__audit_contract_address = mk_checksum_address(
            self.__web3_client,
            self.__audit_contract_address,
        )
        self.__account = mk_checksum_address(
            self.__web3_client,
            self.__account,
        )

        self.__create_audit_contract()
        self.__create_analyzers()
        self.__create_wallet_session_manager()
        self.__create_event_pool_manager()
        self.__create_report_uploader_provider()

    def __load_config(self):
        config_file = io_utils.fetch_file(self.config_file_uri)

        with open(config_file) as yaml_file:
            new_cfg_dict = yaml.load(yaml_file)[self.env]

        try:
            self.__create_components(new_cfg_dict)
            self.__logger.debug("Components successfully created")
            self.__cfg_dict = new_cfg_dict

        except KeyError as missing_config:

            # If this is the first time the loading is happening,
            # nothing to be done except report an exception
            if self.__cfg_dict is None:
                raise Exception(
                    "Incorrect configuration. Missing entry {0}".format(missing_config)
                )

            # Otherwise, the a load happened in the past, and one can
            # revert state to that
            else:
                # Revert configuration as a means to prevent crashes
                self.__logger.debug("Configuration error. Reverting changes....")
                self.__create_components(self.__cfg_dict)
                self.__logger.debug("Successfully reverted changes")

    def __configure_logging(self):
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
                    'level': logging.DEBUG if self.__logging_is_verbose else logging.INFO
                }
            }
        }

        logging.config.dictConfig(dict_config)
        self.__logger = structlog.getLogger("audit")

        if self.__logging_streaming_provider_name is not None:
            self.__create_logging_streaming_provider()
            self.__logger.addHandler(self.__logging_streaming_provider.get_handler())

    def __init__(self, env, config_file_uri, account_passwd=""):
        """
        Builds a Config object from a target environment (e.g., test) and an input YAML
        configuration file.
        """
        self.__env = env
        self.__cfg_dict = None
        self.__account_passwd = account_passwd
        self.__config_file_uri = config_file_uri
        self.__load_config()

    def __raise_err(self, cond=True, msg=""):
        """
        Raises an exception if the given condition holds.
        """
        if cond:
            raise Exception("Cannot initialize QSP node. {0}".format(msg))

    @property
    def eth_provider(self):
        """
        Returns the Ethereum provider object.
        """
        return self.__eth_provider

    @property
    def eth_provider_name(self):
        """
        Returns the Ethereum provider name.
        """
        return self.__eth_provider_name

    @property
    def eth_provider_args(self):
        """
        Returns the arguments required for instantiating the target Ethereum provider.
        """
        return self.__eth_provider_args

    @property
    def audit_contract_address(self):
        """
        Returns the audit QSP contract address.
        """
        return self.__audit_contract_address

    @property
    def min_price(self):
        """
        Return the minimum QSP price for accepting an audit.
        """
        return self.__min_price

    @property
    def evt_polling(self):
        """
        Returns the polling for audit requests frequency (given in seconds).
        """
        return self.__evt_polling_sec

    @property
    def report_uploader(self):
        """
        Returns report uploader."
        """
        return self.__report_uploader

    @property
    def account(self):
        """
        Returns the account numeric identifier to sign reports.
        """
        return self.__account

    @property
    def account_ttl(self):
        """
        Returns the account TTL.
        """
        return self.__account_ttl

    @property
    def account_passwd(self):
        """
        Returns the account associated password.
        """
        return self.__account_passwd

    @property
    def audit_contract_abi_uri(self):
        """
        Returns the audit contract ABI URI.
        """
        return self.__audit_contract_abi_uri

    @property
    def audit_contract_src_uri(self):
        """"
        Returns the audit contract source URI.
        """
        return self.__audit_contract_src_uri

    @property
    def audit_contract_src_deploy(self):
        """
        Returns whether the audit contract source code, once compiled, should
        be deployed on the target network.
        """
        return self.__audit_contract_src_deploy

    @property
    def has_audit_contract_src(self):
        """
        Returns whether the audit contract has been made available.
        """
        return self.__has_audit_contract_src

    @property
    def has_audit_contract_abi(self):
        """
        Returns whether the audit contract ABI has been made available.
        """
        return self.__has_audit_contract_abi

    @property
    def web3_client(self):
        """
        Returns the Web3 client object built from the given YAML configuration file.
        """
        return self.__web3_client

    @property
    def audit_contract(self):
        """
        Returns the audit contract object built from the given YAML configuration file.
        """
        return self.__audit_contract

    @property
    def audit_contract_name(self):
        """
        Returns the name of the audit contract.
        """
        return self.__audit_contract_name

    @property
    def analyzers(self):
        """
        Returns the analyzer object built from the given YAML configuration file.
        """
        return self.__analyzers

    @property
    def wallet_session_manager(self):
        return self.__wallet_session_manager

    @property
    def env(self):
        """
        Returns the target environment to which the settings refer to.
        """
        return self.__env

    @property
    def default_gas(self):
        """
        Returns a fixed amount of gas to be used when interacting with the audit contract.
        """
        return self.__default_gas

    @property
    def config_file_uri(self):
        """
        Returns the configuration file URI.
        """
        return self.__config_file_uri

    @property
    def evt_db_path(self):
        """
        Returns the event pool database path.
        """
        return self.__evt_db_path

    @property
    def submission_timeout_limit_blocks(self):
        """
        Returns the event pool database path.
        """
        return self.__submission_timeout_limit_blocks

    @property
    def event_pool_manager(self):
        """
        Returns the event pool manager.
        """
        return self.__event_pool_manager

    @property
    def logger(self):
        """
        Returns the configured logger.
        """
        return self.__logger

    @property
    def metric_collection_is_enabled(self):
        """
        Is metric collection enabled.
        """
        return self.__metric_collection_is_enabled

    @property
    def metric_collection_interval_seconds(self):
        """
        Metric collection interval in seconds.
        """
        return self.__metric_collection_interval_seconds
