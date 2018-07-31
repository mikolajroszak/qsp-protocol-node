"""
Provides the configuration for executing a QSP Audit node,
as loaded from an input YAML file.
"""
import utils.io as io_utils

from os.path import expanduser
from dpath.util import get

from evt import EventPoolManager
from urllib.parse import urljoin
from utils.eth import (
    mk_checksum_address,
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

    def __fetch_audit_contract_metadata(self, cfg, config_utils):
        metadata_uri = config_utils.resolve_version(config_value(cfg, '/audit_contract_abi/metadata'))
        if metadata_uri is not None:
            return io_utils.load_json(
                io_utils.fetch_file(metadata_uri)
            )

    def __setup_values(self, cfg, config_utils):
        audit_contract_metadata = self.__fetch_audit_contract_metadata(cfg, config_utils)
        self.__audit_contract_name = config_value(audit_contract_metadata, '/contractName')
        self.__audit_contract_address = config_value(audit_contract_metadata, '/contractAddress')
        self.__contract_version = config_value(audit_contract_metadata, '/version')
        self.__audit_contract = None
        self.__audit_contract_abi_uri = config_utils.resolve_version(config_value(cfg, '/audit_contract_abi/uri'))
        self.__eth_provider_name = config_value(cfg, '/eth_node/provider', accept_none=False)
        self.__eth_provider = None
        self.__eth_provider_args = config_value(cfg, '/eth_node/args', {})

        # Makes sure the endpoint URL contains the authentication token
        endpoint = self.__eth_provider_args.get('endpoint_uri')
        if endpoint is not None:
            self.__eth_provider_args['endpoint_uri'] = endpoint.replace("${token}", self.auth_token)

        self.__block_discard_on_restart = config_value(cfg, '/block_discard_on_restart', 0)
        self.__min_price = config_value(cfg, '/min_price', accept_none=False, )
        self.__max_assigned_requests = config_value(cfg, '/max_assigned_requests', accept_none=False)
        self.__evt_polling_sec = config_value(cfg, '/evt_polling_sec', accept_none=False)
        self.__block_mined_polling_interval_sec = config_value(cfg, '/block_mined_polling_interval_sec', accept_none=False)
        self.__analyzers = []
        self.__analyzers_config = config_value(cfg, '/analyzers', accept_none=False)
        self.__account = config_value(cfg, '/account/id', )
        self.__account_keystore_file = config_value(cfg, '/account/keystore_file', None)
        self.__account_private_key = None
        self.__gas = config_value(cfg, '/gas')
        self.__evt_db_path = config_value(cfg, '/evt_db_path', expanduser("~") + "/" + ".audit_node.db")
        self.__submission_timeout_limit_blocks = config_value(cfg, '/submission_timeout_limit_blocks', 10)
        self.__start_n_blocks_in_the_past = config_value(cfg, '/start_n_blocks_in_the_past', 0)
        self.__default_gas = config_value(cfg, '/default_gas')
        self.__gas_price_wei = config_value(cfg, '/gas_price_wei')
        self.__report_uploader_provider_name = config_value(cfg, '/report_uploader/provider')
        self.__report_uploader_provider_args = config_value(cfg, '/report_uploader/args', {})
        self.__logging_is_verbose = config_value(cfg, '/logging/is_verbose', False)
        self.__logging_streaming_provider_name = config_value(cfg, '/logging/streaming/provider')
        self.__logging_streaming_provider_args = config_value(cfg, '/logging/streaming/args', {})
        self.__metric_collection_is_enabled = config_value(cfg, '/metric_collection/is_enabled', False)
        self.__metric_collection_interval_seconds = config_value(cfg, '/metric_collection/interval_seconds', 30)

    def __create_eth_provider(self, config_utils):
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
        return config_utils.create_eth_provider(self.eth_provider_name,
                                                self.eth_provider_args)

    def __create_report_uploader_provider(self, config_utils):
        """
        Creates a report uploader provider.
        """
        return config_utils.create_report_uploader_provider(self.account,
                                                            self.report_uploader_provider_name,
                                                            self.report_uploader_provider_args)

    def __create_web3_client(self, config_utils):
        """
        Creates a Web3 client from the already set Ethereum provider.
        """
        return config_utils.create_web3_client(self.eth_provider, self.account, self.account_passwd, self.account_keystore_file)

    def __create_audit_contract(self, config_utils):
        """
        Creates the audit contract either from its ABI or from its source code (whichever is
        available).
        """
        return config_utils.create_audit_contract(self.web3_client, self.audit_contract_abi_uri,
                                                  self.audit_contract_address)

    def __create_analyzers(self, config_utils):
        """
        Creates an instance of the each target analyzer that should be verifying a given contract.
        """
        return config_utils.create_analyzers(self.analyzers_config, self.logger)

    def __configure_logging(self, config_utils):
        """
        Configures and logging and creates a logger and logging streaming provider.
        """
        return config_utils.configure_logging(self.logging_is_verbose, self.logging_streaming_provider_name,
                                              self.logging_streaming_provider_args, self.account)

    def __create_components(self, config_utils, validate_contract_settings=True):
        # Setup followed by verification
        self.__logger, self.__logging_streaming_provider = self.__configure_logging(config_utils)

        # Contract settings validation
        if validate_contract_settings:
            config_utils.check_audit_contract_settings(self)

        # Creation of internal components
        self.__eth_provider = self.__create_eth_provider(config_utils)
        self.__web3_client, self.__account, self.__account_private_key = self.__create_web3_client(config_utils)

        # After having a web3 client object, use it to put addresses in a canonical format
        self.__audit_contract_address = mk_checksum_address(
            self.__web3_client,
            self.__audit_contract_address,
        )
        self.__account = mk_checksum_address(
            self.__web3_client,
            self.__account,
        )

        if self.has_audit_contract_abi:
            self.__audit_contract = self.__create_audit_contract(config_utils)
        self.__analyzers = self.__create_analyzers(config_utils)
        self.__event_pool_manager = EventPoolManager(self.evt_db_path, self.logger)
        self.__report_uploader = self.__create_report_uploader_provider(config_utils)

    def load_config(self, config_utils, env, config_file_uri, account_passwd="", auth_token="", validate_contract_settings=True):
        self.__config_file_uri = config_file_uri
        self.__env = env
        self.__account_passwd = account_passwd
        self.__auth_token = auth_token
        cfg = config_utils.load_config(config_file_uri, env)
        self.__setup_values(cfg, config_utils)
        self.__create_components(config_utils, validate_contract_settings)
        self.__logger.debug("Components successfully created")
        self.__cfg_dict = cfg

    def __init__(self):
        """
        Builds a Config object from a target environment (e.g., test) and an input YAML
        configuration file.
        """
        self.__node_version = '1.0.0'
        self.__analyzers = []
        self.__analyzers_config = []
        self.__audit_contract_name = None
        self.__audit_contract_address = None
        self.__audit_contract_abi_uri = None
        self.__audit_contract = None
        self.__account = None
        self.__account_keystore_file = None
        self.__account_private_key = None
        self.__account_passwd = None
        self.__auth_token = None
        self.__cfg_dict = None
        self.__config_file_uri = None
        self.__gas = 0
        self.__evt_db_path = None
        self.__evt_polling_sec = 0
        self.__event_pool_manager = None
        self.__env = None
        self.__eth_provider_name = None
        self.__eth_provider_args = None
        self.__eth_provider = None
        self.__gas_price_wei = 0
        self.__logger = None
        self.__logging_is_verbose = False
        self.__logging_streaming_provider_name = None
        self.__logging_streaming_provider_args = None
        self.__logging_streaming_provider = None
        self.__min_price = 0
        self.__metric_collection_is_enabled = True
        self.__metric_collection_interval_seconds = 30
        self.__report_uploader = None
        self.__report_uploader_provider_name = None
        self.__report_uploader_provider_args = None
        self.__start_n_blocks_in_the_past = 0
        self.__submission_timeout_limit_blocks = 10
        self.__web3_client = None
        self.__block_discard_on_restart = 0
        self.__contract_version = None

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
    def block_discard_on_restart(self):
        """
        Returns the number of blocks needed to be available for a request to be analyzed upon
        restart of the auditing node.
        """
        return self.__block_discard_on_restart

    @property
    def audit_contract_address(self):
        """
        Returns the audit QSP contract address.
        """
        return self.__audit_contract_address

    @property
    def min_price(self):
        """
        Returns the minimum QSP price for accepting an audit.
        """
        return self.__min_price

    @property
    def max_assigned_requests(self):
        """
        Returns the maximum number of undone requests
        """
        return self.__max_assigned_requests

    @property
    def evt_polling(self):
        """
        Returns the polling for audit requests frequency (given in seconds).
        """
        return self.__evt_polling_sec

    @property
    def block_mined_polling(self):
        """
        Returns the polling for checking if a new block is mined (given in seconds).
        """
        return self.__block_mined_polling_interval_sec

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
    def account_private_key(self):
        """
        Returns the account private key.
        """
        return self.__account_private_key

    @property
    def account_passwd(self):
        """
        Returns the account associated password.
        """
        return self.__account_passwd

    @property
    def auth_token(self):
        """
        Returns the authentication token required to access the provider endpoint.
        """
        return self.__auth_token

    @property
    def account_keystore_file(self):
        """
        Returns the account keystore file.
        """
        return self.__account_keystore_file

    @property
    def audit_contract_abi_uri(self):
        """
        Returns the audit contract ABI URI.
        """
        return self.__audit_contract_abi_uri

    @property
    def has_audit_contract_abi(self):
        """
        Returns whether the audit contract ABI has been made available.
        """
        return bool(self.__audit_contract_abi_uri)

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
    def env(self):
        """
        Returns the target environment to which the settings refer to.
        """
        return self.__env

    @property
    def gas(self):
        """
        Returns a fixed amount of gas to be used when interacting with the audit contract.
        """
        return self.__gas

    @property
    def gas_price_wei(self):
        """
        Returns default gas price.
        """
        return self.__gas_price_wei

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
    def start_n_blocks_in_the_past(self):
        """
        Returns how many blocks in the past should be considered if an empty database
        """
        return self.__start_n_blocks_in_the_past

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

    @property
    def logging_streaming_provider(self):
        return self.__logging_streaming_provider

    @property
    def report_uploader_provider_name(self):
        return self.__report_uploader_provider_name

    @property
    def report_uploader_provider_args(self):
        return self.__report_uploader_provider_args

    @property
    def analyzers_config(self):
        return self.__analyzers_config

    @property
    def logging_is_verbose(self):
        return self.__logging_is_verbose

    @property
    def logging_streaming_provider_name(self):
        return self.__logging_streaming_provider_name

    @property
    def logging_streaming_provider_args(self):
        return self.__logging_streaming_provider_args

    @property
    def contract_version(self):
        """
        The version of the associated smart contract
        """
        return self.__contract_version

    @property
    def node_version(self):
        """
        The version of the associated smart contract
        """
        return self.__node_version
