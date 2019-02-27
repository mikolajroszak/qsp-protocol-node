####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import os

import utils.io as io_utils

from audit import (
    Analyzer,
    Wrapper
)
from stream_logger import get_logger

from pathlib import Path
from tempfile import gettempdir
from time import sleep
from upload import S3Provider, DummyProvider
from utils.eth import mk_read_only_call
from web3 import (
    Web3,
    HTTPProvider,
    IPCProvider,
    EthereumTesterProvider,
)

# TODO Retire this code altogether in favor of module-specific factories
class ConfigurationException(Exception):
    """
    A specialized exception for throwing from this class.
    """


class ConfigUtils:
    """
    A utility class that helps with creating the configuration object.
    """
    __APPROXIMATE_BLOCK_LENGTH_IN_SECONDS = 12

    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract/blob/develop
    #       /contracts/QuantstampAuditData.sol#L43
    __AUDIT_TIMEOUT_IN_BLOCKS = 50

    @classmethod
    def load_config(cls, config_file_uri, environment):
        """
        Loads config from file and returns.
        """
        config_file_path = io_utils.fetch_file(config_file_uri)
        config_file = io_utils.load_yaml(config_file_path)
        return config_file[environment]

    def __init__(self, node_version):
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__node_version = node_version

    def create_web3_client(self,
                           eth_provider,
                           account_passwd,
                           keystore_file,
                           max_attempts=30):
        """
        Creates a Web3 client from the already set Ethereum provider, and creates and account.
        """
        attempts = 0

        # Default retry policy is as follows:
        # 1) Makes a query (in this case, "eth.accounts")
        # 2) If connected, nothing else to do
        # 3) Otherwise, keep trying at most max_attempts, waiting 10s per each iteration
        web3_client = Web3(eth_provider)
        new_account = None
        new_private_key = None
        connected = False

        while attempts < max_attempts and not connected:
            try:
                web3_client = Web3(eth_provider)
                # the following throws if Geth is not reachable
                web3_client.eth.accounts
                connected = True
                self.__logger.debug("Connected on attempt {0}".format(attempts))
            except Exception as exception:
                # An exception has occurred. Increment the number of attempts
                # made, and retry after 5 seconds
                attempts = attempts + 1
                self.__logger.debug(
                    "Connection attempt ({0}) failed due to {1}. Retrying in 10 seconds".format(attempts, str(exception)))
                sleep(10)

        if not connected:
            raise ConfigurationException(
                "Could not connect to ethereum node (time out after {0} attempts).".format(
                    max_attempts
                )
            )

        # It could be the case that account is not setup, which may happen for
        # test-related providers (e.g., EthereumTestProvider)
        if keystore_file is None:
            if eth_provider.__class__.__name__ not in ['EthereumTesterProvider']:
                raise ConfigurationException("Could not find an account. Please provide a valid keystore file")

            new_account = web3_client.eth.accounts[0]
            self.__logger.debug("No account was provided, using the account at index [0]", account=new_account)
        else:
            try:
                with open(keystore_file) as keyfile:
                    encrypted_key = keyfile.read()
                    new_private_key = web3_client.eth.account.decrypt(encrypted_key, account_passwd)
                    acct = web3_client.eth.account.privateKeyToAccount(new_private_key)
                    new_account = acct.address
            except Exception as exception:
                raise ConfigurationException("Error reading or decrypting the keystore file '{0}': {1}".format(
                    keystore_file,
                    exception)
                )
        return web3_client, new_account, new_private_key

    def check_configuration_settings(self, config):
        """
        Performs sanity checks on configuration parameters.
        """
        # collect state variables from the smart contract
        call = config.audit_contract.functions.getAuditTimeoutInBlocks()
        contract_audit_timeout_in_blocks = mk_read_only_call(config, call)
        call = config.audit_contract.functions.getMaxAssignedRequests()
        contract_max_assigned_requests = mk_read_only_call(config, call)

        # start_n_blocks_in_the_past should never exceed the submission timeout
        ConfigUtils.raise_err(config.start_n_blocks_in_the_past > config.submission_timeout_limit_blocks)

        # the submission timeout limit should not exceed the audit timeout limit
        ConfigUtils.raise_err(config.submission_timeout_limit_blocks > contract_audit_timeout_in_blocks)

        # the analyzer timeouts should never exceed the audit timeout (converted to seconds)
        for analyzer in config.analyzers:
            analyzer_timeout = analyzer.wrapper.timeout_sec
            ConfigUtils.raise_err(
                analyzer_timeout > contract_audit_timeout_in_blocks * ConfigUtils.__APPROXIMATE_BLOCK_LENGTH_IN_SECONDS)

        # max assigned requests should never exceed the limit specified in the contract
        ConfigUtils.raise_err(config.max_assigned_requests > contract_max_assigned_requests)

        # default gas price should never exceed max gas price, if set
        if config.max_gas_price_wei > 0:
            ConfigUtils.raise_err(config.default_gas_price_wei > config.max_gas_price_wei)

        # the gas price strategy can be either dynamic or static
        ConfigUtils.raise_err(config.gas_price_strategy not in ['dynamic', 'static'])

        # the n-blocks confirmation amount should never exceed the audit timeout in blocks
        ConfigUtils.raise_err(config.n_blocks_confirmation > ConfigUtils.__AUDIT_TIMEOUT_IN_BLOCKS)

        # the n-blocks confirmation amount should not be negative
        ConfigUtils.raise_err(config.n_blocks_confirmation < 0)

    def check_audit_contract_settings(self, config):
        """
        Checks the configuration values provided in the YAML configuration file.
        The contract ABI and source code are mutually exclusive, but one has to be provided.
        This must similarly be checked for QuantstampAuditData.
        """
        if config.has_audit_contract_abi:
            has_uri = bool(config.audit_contract_abi_uri)
            has_addr = bool(config.audit_contract_address)
            ConfigUtils.raise_err(not (has_uri and has_addr),
                                  "Missing audit contract ABI URI and address",
                                  )
        else:
            ConfigUtils.raise_err(msg="Missing the audit contract ABI")

    def create_contract(self, web3_client, contract_abi_uri, contract_address):
        """
        Creates the audit contract from ABI.
        """
        abi_file = io_utils.fetch_file(contract_abi_uri)
        abi_json = io_utils.load_json(abi_file)

        return web3_client.eth.contract(
            address=contract_address,
            abi=abi_json,
        )

    def resolve_version(self, version):
        """
        Instruments a given string with the version of the protocol
        """
        major_version = self.__node_version[0:self.__node_version.index('.')]
        result = None
        if version is not None:
            result = version.replace('{major-version}', major_version)
        return result

    def create_analyzers(self, analyzers_config):
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

            # Gets ths single key in the dictionary (the name of the analyzer)
            analyzer_name = list(analyzer_config_dict.keys())[0]
            analyzer_config = analyzers_config[i][analyzer_name]
            script_path = os.path.realpath(__file__)
            wrappers_dir = '{0}/../../../plugins/analyzers/wrappers'.format(os.path.dirname(script_path))

            wrapper = Wrapper(
                wrappers_dir=wrappers_dir,
                analyzer_name=analyzer_name,
                args=analyzer_config.get('args', ""),
                storage_dir=analyzer_config.get('storage_dir', default_storage),
                timeout_sec=analyzer_config.get('timeout_sec', default_timeout_sec)
            )

            default_storage = "{0}/.{1}".format(
                str(Path.home()),
                analyzer_name,
            )

            analyzers.append(Analyzer(wrapper))

        return analyzers

    @staticmethod
    def raise_err(cond=True, msg=""):
        """
        Raises an exception if the given condition holds.
        """
        if cond:
            raise ConfigurationException("Cannot initialize QSP node. {0}".format(msg))
