"""
Provides the configuration for executing a QSP Audit node, 
as loaded from an input YAML file.
"""
from web3 import Web3, TestRPCProvider, HTTPProvider, IPCProvider, EthereumTesterProvider
from dpath.util import get
from solc import compile_files

import yaml
import re
import utils.io as io_utils

from audit import Analyzer


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
    def __setup_values(self, cfg):
        self.__internal_contract_abi_uri = config_value(cfg, '/internal_contract_abi/uri')
        self.__internal_contract_address = config_value(cfg, '/internal_contract_abi/address')
        self.__internal_contract_name = config_value(cfg, '/internal_contract_abi/name')
        self.__has_internal_contract_abi = bool(self.__internal_contract_abi_uri)

        self.__internal_contract_src_uri = config_value(cfg, '/internal_contract_src/uri')
        self.__internal_contract_src_deploy = config_value(cfg, '/internal_contract_src/deploy', False)
        self.__internal_contract_name = config_value(cfg, '/internal_contract_src/name')
        self.__has_internal_contract_src = bool(self.__internal_contract_src_uri)

        self.__eth_provider = config_value(cfg, '/eth_node/provider', accept_none=False)
        self.__eth_provider_args = config_value(cfg, '/eth_node/args', {})
        self.__min_price = config_value(cfg, '/min_price', accept_none=False)
        self.__evt_polling_sec = config_value(cfg, '/evt_polling_sec', accept_none=False)
        self.__analyzer_output = config_value(cfg, '/analyzer/output', accept_none=False)
        self.__analyzer_cmd = config_value(cfg, '/analyzer/cmd', accept_none=False)
        self.__account_id = config_value(cfg, '/account_id', accept_none=False)
        self.__solidity_version = config_value(cfg, '/analyzer/solidity', accept_none=False)

    def __check_values(self):
        """
        Checks the configuration values provided in the YAML configuration file.
        """
        self.__check_internal_contract_settings()
        self.__check_solidity_version()

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
            deploy = bool(self.__internal_contract_src_deploy)
            self.__raise_err(
                not (deploy or has_uri),  
                "Missing internal contract source deploy flag and its URI", 
            )
        else:
            self.__raise_err(msg="Missing the internal contract source or its ABI")

    def __check_solidity_version(self):
            """
            Checks the format of the supported solidity version.
            """
            self.__raise_err(
                 not bool(re.match("[0-9]+\.[0-9]+\.[0-9]+", self.__solidity_version)),
                "Solidity version is not correct",
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

        if self.__eth_provider == "HTTPProvider":
            self.__eth_provider = HTTPProvider(**self.__eth_provider_args)
            return

        if self.__eth_provider == "IPCProvider":
            self.__eth_provider = IPCProvider(**self.__eth_provider_args)
            return
            
        if self.__eth_provider == "EthereumTesterProvider":
            # NOTE: currently relies on the legacy EthereumTesterProvider,
            # instead of having something like
            #
            # from web3 import Web3
            # from web3.providers.eth_tester import EthereumTesterProvider
            # from eth_tester import EthereumTester
            # eth_tester = EthereumTester()
            # provider = EthereumTesterProvider(eth_tester))
            #
            # The reason of that relies on bugs related to 
            # how keys are stored in events (given as dictionaries).
            #
            # See https://github.com/ethereum/web3.py/issues/503
            # for further information.
            self.__eth_provider = EthereumTesterProvider()
            return

        if self.__eth_provider == "TestRPCProvider":
            self.__eth_provider = TestRPCProvider(**self.__eth_provider_args)
            return

        raise Exception("Unknown/Unsupported provider: {0}".format(self.eth_provider))

    def __create_web3_client(self):
        """
        Creates a Web3 client from the already set Ethereum provider.
        """
        self.__web3_client = Web3(self.eth_provider)

    def __load_contract_from_src(self):
        """
        Loads the internal contract from source code (useful for testing purposes).
        """
        # Compile the source
        src_contract = io_utils.fetch_file(self.__internal_contract_src_uri)
        contract_dict = compile_files([src_contract])

        contract_id = "{0}:{1}".format(
            self.__internal_contract_src_uri,
            self.__internal_contract_name,
        )
        
        # Get the contract interface
        contract_interface = contract_dict[contract_id]

        # Instantiate the contract
        contract = self.web3_client.eth.contract(abi = contract_interface['abi'], bytecode = contract_interface['bin'])
        account = self.web3_client.eth.accounts[self.__account_id]
        
        # Deploy the contract
        transaction_hash = contract.deploy(transaction = {'from': account})

        receipt = self.web3_client.eth.getTransactionReceipt(transaction_hash)
        self.__internal_contract_address = receipt['contractAddress']

        # Creates the contract object
        return self.web3_client.eth.contract(contract_interface['abi'], self.__internal_contract_address)
    
    def __create_internal_contract(self):
        """
        Creates the internal contract either from its ABI or from its source code (whichever is available).
        """
        self.__internal_contract = None

        if self.__has_internal_contract_abi:
            # Create contract from ABI settings

            abi_file = io_utils.fetch_file(self.internal_contract_abi_uri)
            abi_json = io_utils.load_json(abi_file)

            self.__internal_contract = self.web3_client.eth.contract(
                abi_json, 
                self.internal_contract_address,
            )
            
        else:
            self.__internal_contract = self.__load_contract_from_src()

    def __create_analyzer(self):
        """
        Creates an instance of the the target analyzer that verifies a given contract.
        """
        self.__analyzer = Analyzer(
            self.analyzer_cmd,
            self.supported_solidity_version
        )
        
    def __init__(self, env, config_file_uri):
        """
        Builds a Config object from a target environment (e.g., test) and an input YAML configuration file. 
        """
        config_file = io_utils.fetch_file(config_file_uri)

        with open(config_file) as yaml_file:
            cfg = yaml.load(yaml_file)[env]

        try:
            # Setup followed by verification
            self.__setup_values(cfg)
            self.__check_values()

            # Creation of internal components
            self.__create_eth_provider()
            self.__create_web3_client()
            self.__create_internal_contract()
            self.__create_analyzer()
        
        except KeyError as missing_config:
            raise Exception("Incorrect configuration. Missing entry {0}".format(missing_config))

    def __raise_err(self, cond = True, msg = ""):
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
    def supported_solidity_version(self):
        """
        Returns the Solidity version supported by the current QSP audit node."
        """
        return self.__solidity_version

    @property
    def account_id(self):
        """
        Returns the account numeric identifier to sign reports.
        """
        return self.__account_id

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
    def eth_provider_args(self):
        """
        Returns the arguments required for instantiating the target Ethereum provider.
        """
        return self.__eth_provider_args


    
        



            
