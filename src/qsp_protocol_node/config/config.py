####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Provides the configuration for executing a QSP Audit node,
as loaded from an input YAML file
"""

import utils.io as io_utils

from dpath.util import get
from os.path import expanduser

from audit.report_processing import ReportEncoder
from evt import EventPoolManager
from utils.eth import mk_checksum_address

# FIXME
# There is some technical debt accumulating in this file. Config started simple and therefore justified
# its own existence as a self-contained module. This has to change as we move forward. Break config
# into smaller subconfigs. See QSP-414.
# https://quantstamp.atlassian.net/browse/QSP-414


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
    def __fetch_contract_metadata(self, cfg, config_utils, contract_abi):
        metadata_uri = config_utils.resolve_version(
            config_value(cfg, '/' + contract_abi + '/metadata'))
        if metadata_uri is not None:
            return io_utils.load_json(
                io_utils.fetch_file(metadata_uri)
            )

    def __setup_values(self, cfg, config_utils):
        audit_contract_metadata = self.__fetch_contract_metadata(cfg, config_utils,
                                                                 'audit_contract_abi')
        self.__audit_contract_name = config_value(audit_contract_metadata, '/contractName')
        self.__audit_contract_address = config_value(audit_contract_metadata, '/contractAddress')
        self.__contract_version = config_value(audit_contract_metadata, '/version')
        self.__audit_contract = None
        self.__audit_contract_abi_uri = config_utils.resolve_version(
            config_value(cfg, '/audit_contract_abi/uri'))

        self.__eth_provider_name = config_value(cfg, '/eth_node/provider', accept_none=False)
        self.__eth_provider = None
        self.__eth_provider_args = config_value(cfg, '/eth_node/args', {})

        # Makes sure the endpoint URL contains the authentication token
        endpoint = self.__eth_provider_args.get('endpoint_uri')
        if endpoint is not None:
            if self.auth_token is None:
                raise ValueError("Authentication token is missing. Cannot set provider endpoint")
            self.__eth_provider_args['endpoint_uri'] = endpoint.replace("${token}", self.auth_token)

        self.__block_discard_on_restart = config_value(cfg, '/block_discard_on_restart', 0)
        self.__min_price_in_qsp = config_value(cfg, '/min_price_in_qsp', accept_none=False)
        self.__tx_timeout_seconds = config_value(cfg, '/tx_timeout_seconds', accept_none=False)
        self.__max_assigned_requests = config_value(cfg, '/max_assigned_requests',
                                                    accept_none=False)
        self.__evt_polling_sec = config_value(cfg, '/evt_polling_sec', accept_none=False)
        self.__block_mined_polling_interval_sec = config_value(cfg,
                                                               '/block_mined_polling_interval_sec',
                                                               accept_none=False)
        self.__analyzers = []
        self.__analyzers_config = config_value(cfg, '/analyzers', accept_none=False)
        self.__account_keystore_file = config_value(cfg, '/keystore_file', None)
        self.__account_private_key = None
        self.__gas_limit = config_value(cfg, '/gas_limit')
        self.__evt_db_path = config_value(cfg, '/evt_db_path',
                                          expanduser("~") + "/" + ".audit_node.db")
        self.__submission_timeout_limit_blocks = config_value(cfg,
                                                              '/submission_timeout_limit_blocks',
                                                              10)
        self.__start_n_blocks_in_the_past = config_value(cfg, '/start_n_blocks_in_the_past', 0)
        self.__n_blocks_confirmation = config_value(cfg, '/n_blocks_confirmation', 6)
        self.__gas_price_strategy = config_value(cfg, '/gas_price/strategy', accept_none=False)
        self.__default_gas_price_wei = config_value(cfg, '/gas_price/default_gas_price_wei', 0)
        self.__gas_price_wei = self.__default_gas_price_wei
        self.__max_gas_price_wei = config_value(cfg, '/gas_price/max_gas_price_wei', -1)

        self.__upload_provider_name = config_value(cfg, '/upload_provider/name', "")
        self.__upload_provider_is_enabled = config_value(cfg, '/upload_provider/is_enabled', False)
        self.__upload_provider_args = config_value(cfg, '/upload_provider/args', {})
        self.__metric_collection_is_enabled = config_value(cfg, '/metric_collection/is_enabled',
                                                           False)
        self.__metric_collection_destination_endpoint = config_value(cfg, '/metric_collection/destination_endpoint',
                                                           None)
        self.__metric_collection_interval_seconds = config_value(cfg,
                                                                 '/metric_collection/interval_seconds',
                                                                 30)
        self.__heartbeat_allowed = config_value(cfg, '/heartbeat_allowed', True)
        self.__enable_police_audit_polling = config_value(cfg, '/police/is_auditing_enabled', False)

    def __create_eth_provider(self, config_utils):
        """
        Creates an Ethereum provider.
        """
        # Known providers according to Web3
        #
        # HTTPProvider
        # IPCProvider
        # EthereumTesterProvider
        #
        # See: http://web3py.readthedocs.io/en/stable/providers.html
        return config_utils.create_eth_provider(self.eth_provider_name,
                                                self.eth_provider_args)

    def __create_upload_provider(self, config_utils):
        """
        Creates a report upload provider.
        """
        return config_utils.create_upload_provider(self.account,
                                                   self.upload_provider_name,
                                                   self.upload_provider_args,
                                                   self.upload_provider_is_enabled)

    def __create_web3_client(self, config_utils):
        """
        Creates a Web3 client from the already set Ethereum provider.
        """
        return config_utils.create_web3_client(self.eth_provider,
                                               self.account_passwd,
                                               self.account_keystore_file,
                                               )

    def __create_audit_contract(self, config_utils):
        """
        Creates the audit contract either from its ABI or from its source code (whichever is
        available).
        """
        return config_utils.create_contract(self.web3_client, self.audit_contract_abi_uri,
                                            self.audit_contract_address)

    def __create_analyzers(self, config_utils):
        """
        Creates an instance of the each target analyzer that should be verifying a given contract.
        """
        return config_utils.create_analyzers(self.analyzers_config)

    def __create_components(self, config_utils, validate_contract_settings=True):
        # Creation of internal components
        self.__eth_provider = self.__create_eth_provider(config_utils)
        self.__web3_client, self.__account, self.__account_private_key = self.__create_web3_client(
            config_utils)

        # Contract settings validation
        if validate_contract_settings:
            config_utils.check_audit_contract_settings(self)

        # After having a web3 client object, use it to put addresses in a canonical format
        self.__audit_contract_address = mk_checksum_address(self.__audit_contract_address)
        self.__account = mk_checksum_address(self.__account)

        if self.has_audit_contract_abi:
            self.__audit_contract = self.__create_audit_contract(config_utils)

        if validate_contract_settings:
            config_utils.check_configuration_settings(self)

        self.__analyzers = self.__create_analyzers(config_utils)
        self.__event_pool_manager = EventPoolManager(self.evt_db_path)
        self.__report_encoder = ReportEncoder()
        self.__upload_provider = self.__create_upload_provider(config_utils)

    def load_dictionary(self, config_dictionary, config_utils, env, account_passwd="", auth_token="",
                        validate_contract_settings=True):
        self.__env = env
        self.__account_passwd = account_passwd
        self.__auth_token = auth_token
        self.__setup_values(config_dictionary, config_utils)
        self.__create_components(config_utils, validate_contract_settings)

    def load_file(self, config_file_uri, config_utils, env, account_passwd="", auth_token="",
                    validate_contract_settings=True):
        cfg = config_utils.load_config(config_file_uri, env)
        self.__config_file_uri = config_file_uri
        self.load_dictionary(cfg, config_utils, env, account_passwd, auth_token, validate_contract_settings)

    def __init__(self):
        """
        Builds a Config object from a target environment (e.g., test) and an input YAML
        configuration file.
        """
        self.__node_version = '2.0.2'
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
        self.__config_file_uri = None
        self.__gas_limit = 0
        self.__evt_db_path = None
        self.__evt_polling_sec = 0
        self.__event_pool_manager = None
        self.__env = None
        self.__eth_provider_name = None
        self.__eth_provider_args = None
        self.__eth_provider = None
        self.__gas_price_strategy = "dynamic"
        self.__default_gas_price_wei = 0
        self.__gas_price_wei = 0
        self.__max_gas_price_wei = -1
        self.__min_price_in_qsp = 0
        self.__tx_timeout_seconds = 300
        self.__metric_collection_is_enabled = True
        self.__metric_collection_interval_seconds = 30
        self.__report_encoder = None
        self.__metric_collection_destination_endpoint = None
        self.__upload_provider = None
        self.__upload_provider_is_enabled = False
        self.__upload_provider_name = None
        self.__upload_provider_args = None
        self.__start_n_blocks_in_the_past = 0
        self.__n_blocks_confirmation = 6
        self.__submission_timeout_limit_blocks = 10
        self.__web3_client = None
        self.__block_discard_on_restart = 0
        self.__contract_version = None
        self.__heartbeat_allowed = True
        self.__enable_police_audit_polling = False

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
    def min_price_in_qsp(self):
        """
        Returns the minimum QSP price for accepting an audit.
        """
        return self.__min_price_in_qsp

    @property
    def tx_timeout_seconds(self):
        """
        Returns the timeout for performing transaction
        """
        return self.__tx_timeout_seconds

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
    def report_encoder(self):
        """
        Returns report encoder.
        """
        return self.__report_encoder

    @property
    def upload_provider(self):
        """
        Returns report upload provider.
        """
        return self.__upload_provider

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
    def gas_limit(self):
        """
        Returns a fixed amount of gas to be used when interacting with the audit contract.
        """
        return self.__gas_limit

    @property
    def gas_price_strategy(self):
        """
        Returns the strategy for configuring the gas price of transactions
        """
        return self.__gas_price_strategy

    @property
    def default_gas_price_wei(self):
        """
        Returns default gas price.
        """
        return self.__default_gas_price_wei

    @property
    def gas_price_wei(self):
        """
        Returns current gas price.
        """
        return self.__gas_price_wei

    @gas_price_wei.setter
    def gas_price_wei(self, value):
        """
        Sets current gas price.
        """
        self.__gas_price_wei = value

    @property
    def max_gas_price_wei(self):
        """
        Returns default gas price.
        """
        return self.__max_gas_price_wei

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
    def n_blocks_confirmation(self):
        """
        Returns how many blocks the node should wait before declaring a transaction successful
        """
        return self.__n_blocks_confirmation

    @property
    def event_pool_manager(self):
        """
        Returns the event pool manager.
        """
        return self.__event_pool_manager

    @property
    def metric_collection_is_enabled(self):
        """
        Is metric collection enabled.
        """
        return self.__metric_collection_is_enabled

    @property
    def metric_collection_destination_endpoint(self):
        """
        Destrination endpoint where the collected metrics are sent to.
        """
        return self.__metric_collection_destination_endpoint

    @property
    def metric_collection_interval_seconds(self):
        """
        Metric collection interval in seconds.
        """
        return self.__metric_collection_interval_seconds

    @property
    def upload_provider_is_enabled(self):
        return self.__upload_provider_is_enabled

    @property
    def upload_provider_name(self):
        return self.__upload_provider_name

    @property
    def upload_provider_args(self):
        return self.__upload_provider_args

    @property
    def analyzers_config(self):
        return self.__analyzers_config

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

    @property
    def heartbeat_allowed(self):
        """
        If true, the node will set min price using a blocking call upon startup and then every 24
        hours. Otherwise, it will only update the min price if it differs.
        """
        return self.__heartbeat_allowed

    @property
    def enable_police_audit_polling(self):
        """
        If true, the police node will also poll for regular audit requests.
        """
        return self.__enable_police_audit_polling
