####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Provides functions related to testing resources.
"""
import contextlib
import os

from config import ConfigFactory, ConfigUtils
from .transact import safe_transact
from utils.io import fetch_file, load_json

from dpath.util import get
from solc import compile_files


def resource_uri(path, is_main=False):
    """
    Returns the filesystem URI of a given resource.
    """
    if is_main:
        return "file://{0}/../../src/qsp_protocol_node/{1}".format(os.path.dirname(__file__), path)
    else:
        return "file://{0}/../resources/{1}".format(os.path.dirname(__file__), path)


def project_root():
    """
    Returns the root folder of the audit node project.
    """
    return os.path.abspath("{0}/../../".format(os.path.dirname(__file__)))


def remove(path):
    with contextlib.suppress(FileNotFoundError):
        os.remove(path)


def __load_audit_contract_from_src(web3_client, contract_src_uri, contract_name,
                                constructor_from):
    """
    Loads the QuantstampAuditMock contract from source code returning the (address, contract)
    pair.
    """
    audit_contract_src = fetch_file(contract_src_uri)
    contract_dict = compile_files([audit_contract_src])
    contract_id = "{0}:{1}".format(
        contract_src_uri,
        contract_name,
    )
    contract_interface = contract_dict[contract_id]

    # deploy the audit contract
    audit_contract = web3_client.eth.contract(
        abi=contract_interface['abi'],
        bytecode=contract_interface['bin']
    )
    tx_hash = safe_transact(audit_contract.constructor(),
                           {'from': constructor_from, 'gasPrice': 0})
    receipt = web3_client.eth.getTransactionReceipt(tx_hash)
    address = receipt['contractAddress']
    audit_contract = web3_client.eth.contract(
        abi=contract_interface['abi'],
        address=address,
    )
    return address, audit_contract


def fetch_config(inject_contract=False):
    # create config from file, the contract is not provided and will be injected separately
    uri = resource_uri("test_config.yaml")
    config = ConfigFactory.create_from_file(config_file_uri=uri, 
                                            environment=os.getenv("QSP_ENV", default="dev"),
                                            qsp_home_dir=os.getenv("QSP_HOME"),
                                            validate_contract_settings=False)
    
    if inject_contract:
        contract_source_uri = "{0}/tests/resources/QuantstampAuditMock.sol".format(project_root())
        contract_metadata_uri = "{0}/tests/resources/QuantstampAudit-metadata.json".format(project_root())
        audit_contract_metadata = load_json(fetch_file(contract_metadata_uri))
        audit_contract_name = get(audit_contract_metadata, '/contractName')

        addr, contract = __load_audit_contract_from_src(
            config.web3_client,
            contract_source_uri,
            audit_contract_name,
            config.account)

        config._Config__audit_contract_address = addr
        config._Config__audit_contract = contract

        config_utils = ConfigUtils(config.node_version)
        config_utils.check_configuration_settings(config)

    return config
