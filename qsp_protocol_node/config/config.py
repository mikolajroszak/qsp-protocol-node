"""
Provides the configuration for executing a QSP Audit node,
as loaded from an input YAML file.
"""
from web3 import (
    Web3,
    TestRPCProvider,
    HTTPProvider,
    IPCProvider,
    EthereumTesterProvider,
)
from upload import S3Provider
from streaming import CloudWatchProvider
from dpath.util import get
from solc import compile_files
from os.path import expanduser
from time import sleep

import yaml
import re
import os
import hashlib

import logging
import logging.config
import structlog

from structlog import configure_once, processors, stdlib, threadlocal

import utils.io as io_utils

from audit import Analyzer
from utils.eth import (
    WalletSessionManager, 
    DummyWalletSessionManager,
    mk_checksum_address,
)
from evt import EventPoolManager

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


class Config:
    """
    Provides a set of methods for accessing configuration parameters.
    """

    def __fetch_internal_contract_metadata(self, cfg):
        metadata_uri = config_value(cfg, '/internal_contract_abi/metadata')
        if metadata_uri is not None:
            return io_utils.load_json(
                io_utils.fetch_file(metadata_uri)
            )

        metadata_uri = config_value(cfg, '/internal_contract_src/metadata')
        if metadata_uri is not None:
            return io_utils.load_json(
                io_utils.fetch_file(metadata_uri)
            )

        raise Exception("Missing internal contract metadata")

    def __setup_values(self, cfg):
        metadata = self.__fetch_internal_contract_metadata(cfg)
        self.__internal_contract_name = config_value(
            metadata,
            '/contractName',
        )
        self.__internal_contract_address = config_value(
            metadata,
            '/contractAddress',
        )

        self.__internal_contract = None

        self.__internal_contract_src_uri = config_value(
            cfg,
            '/internal_contract_src/uri',
        )
        self.__has_internal_contract_src = bool(
            self.__internal_contract_src_uri
        )

        self.__internal_contract_abi_uri = config_value(
            cfg,
            '/internal_contract_abi/uri',
        )
        self.__has_internal_contract_abi = bool(
            self.__internal_contract_abi_uri
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
        self.__analyzer_output = config_value(
            cfg,
            '/analyzer/output',
            accept_none=False,
        )
        self.__analyzer_cmd = config_value(
            cfg,
            '/analyzer/cmd',
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

    def __check_values(self):
        """
        Checks the configuration values provided in the YAML configuration file.
        """
        self.__check_internal_contract_settings()

    def __check_internal_contract_settings(self):
        """
        Checks the settings w.r.t. the internal contract.
        """
        self.__raise_err(
            self.__has_internal_contract_abi and self.__has_internal_contract_src,
            "Settings must include internal contract ABI or source, but not both",
        )

        if self.__has_internal_contract_abi:
            has_uri = bool(self.__internal_contract_abi_uri)
            has_addr = bool(self.__internal_contract_address)
            self.__raise_err(
                not (has_uri and has_addr),
                "Missing internal contract ABI URI and address",
            )

        elif self.__has_internal_contract_src:
            has_uri = bool(self.__internal_contract_src_uri)
            self.__raise_err(
                not has_uri,
                "Missing internal contract source URI"
            )
        else:
            self.__raise_err(
                msg="Missing the internal contract source or its ABI")

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
        # 
        # 1) Creates a given provider and checks if it is connected or not
        # 2) If connected, nothing else to do
        # 3) Otherwise, keep trying at most max_attempts, 
        #    waiting 5s per each iteration

        self.__eth_provider = None
        connected = False

        while attempts < max_attempts and not connected:
            try:
                self.__eth_provider = Config.__new_provider(self.__eth_provider_name, self.__eth_provider_args)
                connected = True
            except:
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
            self.__logging_streaming_provider = CloudWatchProvider(**self.__logging_streaming_provider_args)
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
                self.__logger.debug("No account was provided, using a newly created one", account=self.__account)
            else:
                self.__account = self.__web3_client.eth.accounts[0]
                self.__logger.debug("No account was provided, using the account at index [0]", account=self.__account)

    def __load_contract_from_src(self):
        """
        Loads the internal contract from source code (useful for testing purposes).
        """
        # Compiles the source
        src_contract = io_utils.fetch_file(self.__internal_contract_src_uri)
        contract_dict = compile_files([src_contract])

        contract_id = "{0}:{1}".format(
            self.__internal_contract_src_uri,
            self.__internal_contract_name,
        )

        # Gets the contract interface
        contract_interface = contract_dict[contract_id]

        # Instantiates the contract
        contract = self.web3_client.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )

        # Deploys the contract
        transaction_hash = contract.deploy(
            transaction={'from': self.__account})

        receipt = self.web3_client.eth.getTransactionReceipt(transaction_hash)
        self.__internal_contract_address = receipt['contractAddress']

        # Creates the contract object
        return self.web3_client.eth.contract(
		abi=contract_interface['abi'],
		address=self.__internal_contract_address
	)

    def __create_internal_contract(self):
        """
        Creates the internal contract either from its ABI or from its source code (whichever is available).
        """
        self.__internal_contract = None

        if self.__has_internal_contract_abi:
            # Creates contract from ABI settings

            abi_file = io_utils.fetch_file(self.internal_contract_abi_uri)
            abi_json = io_utils.load_json(abi_file)

            self.__internal_contract = self.web3_client.eth.contract(
                address=self.internal_contract_address,
                abi=abi_json,
            )

        else:
            self.__internal_contract = self.__load_contract_from_src()

    def __create_analyzer(self):
        """
        Creates an instance of the the target analyzer that verifies a given contract.
        """
        self.__analyzer = Analyzer(self.analyzer_cmd, self.logger)

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

        # After having a web3 client object, 
        # use it to put addresses in a canonical
        # format
        self.__internal_contract_address = mk_checksum_address(
            self.__web3_client,
            self.__internal_contract_address,
        )
        self.__account = mk_checksum_address(
            self.__web3_client,
            self.__account,
        )

        self.__create_internal_contract()
        self.__create_analyzer()
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
      
      dictConfig = {
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
      };

      if (self.__logging_streaming_provider_name != None):
        self.__create_logging_streaming_provider()
        dictConfig['handlers']['streaming'] = self.__logging_streaming_provider.get_dict_config()
        dictConfig['loggers']['']['handlers'].append('streaming')
        logging.config.dictConfig(dictConfig)
        self.__logger = structlog.getLogger("audit")
        self.__logger.addHandler(self.__logging_streaming_provider.get_handler())
      else:
        logging.config.dictConfig(dictConfig)
        self.__logger = structlog.getLogger("audit")

    def __init__(self, env, config_file_uri, account_passwd=""):
        """
        Builds a Config object from a target environment (e.g., test) and an input YAML configuration file. 
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
    def internal_contract_address(self):
        """
        Returns the internal QSP contract address.
        """
        return self.__internal_contract_address

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
    def analyzer_output(self):
        """
        Returns the output of the analyzer (either 'stdout' or a filename template).
        """
        return self.__analyzer_output

    @property
    def analyzer_cmd(self):
        """
        Returns the analyzer command template."
        """
        return self.__analyzer_cmd

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
    def internal_contract_abi_uri(self):
        """
        Returns the internal contract ABI URI.
        """
        return self.__internal_contract_abi_uri

    @property
    def internal_contract_src_uri(self):
        """"
        Returns the internal contract source URI.
        """
        return self.__internal_contract_src_uri

    @property
    def internal_contract_src_deploy(self):
        """
        Returns whether the internal contract source code, once compiled, should
        be deployed on the target network.
        """
        return self.__internal_contract_src_deploy

    @property
    def has_internal_contract_src(self):
        """
        Returns whether the internal contract has been made available.
        """
        return self.__has_internal_contract_src

    @property
    def has_internal_contract_abi(self):
        """
        Returns whether the internal contract ABI has been made available.
        """
        return self.__has_internal_contract_abi

    @property
    def web3_client(self):
        """ 
        Returns the Web3 client object built from the given YAML configuration file.
        """
        return self.__web3_client

    @property
    def internal_contract(self):
        """
        Returns the internal contract object built from the given YAML configuration file.
        """
        return self.__internal_contract

    @property
    def internal_contract_name(self):
        """
        Returns the name of the internal contract.
        """
        return self.__internal_contract_name

    @property
    def analyzer(self):
        """
        Returns the analyzer object built from the given YAML configuration file.
        """
        return self.__analyzer

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
        Returns a fixed amount of gas to be used when interacting with the internal contract.
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
