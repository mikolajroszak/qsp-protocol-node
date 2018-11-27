####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Tests the mock escrow. This test should be removed when some real tests using the escrow are
developed.
"""
import contextlib
import os
import unittest

from dpath.util import get
from helpers.resource import (
    resource_uri,
)
from solc import compile_files
from timeout_decorator import timeout

from config import ConfigFactory, ConfigUtils
from utils.eth import mk_read_only_call
from utils.eth.singleton_lock import SingletonLock
from utils.io import fetch_file, load_json


class TestEscrow(unittest.TestCase):
    __AUDIT_STATE_SUCCESS = 4
    __AUDIT_STATE_ERROR = 5
    __AVAILABLE_AUDIT_STATE_READY = 1
    __AVAILABLE_AUDIT_STATE_ERROR = 0
    __REQUEST_ID = 1
    __PRICE = 100
    __SLEEP_INTERVAL = 0.01
    __logger = None

    @classmethod
    def __clean_up_file(cls, path):
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)

    @staticmethod
    def __safe_transact(contract_entity, tx_args):
        """
        The contract_entity should already be invoked, so that we can immediately call transact
        """
        try:
            SingletonLock.instance().lock.acquire()
            return contract_entity.transact(tx_args)
        except Exception as e:
            TestEscrow.__logger.exception("!!!!!!! Safe transaction in tests failed")
            raise e
        finally:
            try:
                SingletonLock.instance().lock.release()
            except Exception as error:
                TestEscrow.__logger.exception(
                    "Error when releasing a lock in test {0}".format(str(error))
                )

    @staticmethod
    def __load_audit_contract_from_src(web3_client, contract_src_uri, contract_name,
                                       data_contract_name, constructor_from):
        """
        Loads the QuantstampAuditMock contract from source code returning the (address, contract)
        pair.
        """
        # create the escrow contract
        escrow_contract_src_uri = "./tests/resources/QuantstampAuditTokenEscrow.sol"
        escrow_contract_src = fetch_file(escrow_contract_src_uri)
        escrow_dict = compile_files([escrow_contract_src])
        escrow_id = "{0}:{1}".format(
            escrow_contract_src_uri,
            "QuantstampAuditTokenEscrow",
        )
        print(str(escrow_dict))
        escrow_interface = escrow_dict[escrow_id]

        audit_contract_src = fetch_file(contract_src_uri)
        contract_dict = compile_files([audit_contract_src])
        contract_id = "{0}:{1}".format(
            contract_src_uri,
            contract_name,
        )
        data_contract_id = "{0}:{1}".format(
            contract_src_uri,
            data_contract_name,
        )
        contract_interface = contract_dict[contract_id]
        data_contract_interface = contract_dict[data_contract_id]

        # deploy the data contract
        data_contract = web3_client.eth.contract(
            abi=data_contract_interface['abi'],
            bytecode=data_contract_interface['bin']
        )
        tx_hash = TestEscrow.__safe_transact(data_contract.constructor(),
                                             {'from': constructor_from, 'gasPrice': 0})
        receipt = web3_client.eth.getTransactionReceipt(tx_hash)
        data_address = receipt['contractAddress']
        data_contract = web3_client.eth.contract(
            abi=data_contract_interface['abi'],
            address=data_address,
        )

        # deploy the audit contract
        audit_contract = web3_client.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )
        tx_hash = TestEscrow.__safe_transact(audit_contract.constructor(data_address),
                                             {'from': constructor_from, 'gasPrice': 0})
        receipt = web3_client.eth.getTransactionReceipt(tx_hash)
        address = receipt['contractAddress']
        audit_contract = web3_client.eth.contract(
            abi=contract_interface['abi'],
            address=address,
        )

        # deploy the escrow contract
        escrow_contract = web3_client.eth.contract(
            abi=escrow_interface['abi'],
            bytecode=escrow_interface['bin']
        )
        tx_hash = TestEscrow.__safe_transact(escrow_contract.constructor(data_address),
                                             {'from': constructor_from, 'gasPrice': 0})
        receipt = web3_client.eth.getTransactionReceipt(tx_hash)
        escrow_address = receipt['contractAddress']
        escrow_contract = web3_client.eth.contract(
            abi=contract_interface['abi'],
            address=address,
        )

        # add the escrow contract to the audit contract
        tx_hash = TestEscrow.__safe_transact(
            audit_contract.functions.setTokenEscrow(escrow_address),
            {'from': constructor_from, 'gasPrice': 0})
        web3_client.eth.getTransactionReceipt(tx_hash)
        return address, audit_contract, data_contract, escrow_contract

    def fetch_config(self):
        # create config from file, the contract is not provided and will be injected separately
        config_file_uri = resource_uri("test_config.yaml")
        config = ConfigFactory.create_from_file(os.getenv("QSP_ENV", default="dev"),
                                                config_file_uri,
                                                validate_contract_settings=False)
        # compile and inject contract
        contract_source_uri = "./tests/resources/QuantstampAuditMock.sol"
        contract_metadata_uri = "./tests/resources/QuantstampAudit-metadata.json"
        data_contract_metadata_uri = "./tests/resources/QuantstampAuditData-metadata.json"
        audit_contract_metadata = load_json(fetch_file(contract_metadata_uri))
        data_contract_metadata = load_json(fetch_file(data_contract_metadata_uri))
        audit_contract_name = get(audit_contract_metadata, '/contractName')
        data_contract_name = get(data_contract_metadata, '/contractName')
        config._Config__audit_contract_address, \
        config._Config__audit_contract, \
        config._Config__audit_data_contract, \
        self.escrow_contract = TestEscrow.__load_audit_contract_from_src(config.web3_client,
                                                                         contract_source_uri,
                                                                         audit_contract_name,
                                                                         data_contract_name,
                                                                         config.account)

        config_utils = ConfigUtils(config.node_version)
        config_utils.check_configuration_settings(config)
        return config

    def setUp(self):
        """
        Deploys the contracts.
        """
        config = self.fetch_config()
        TestEscrow.__logger = config.logger
        self.__config = config

    @timeout(10, timeout_exception=StopIteration)
    def test_staking(self):
        """
        Tests interaction with staking contract via the audit contract.
        """
        self.__stake(300)
        self.assertEqual(300, self.__get_total_stake())

    def __get_total_stake(self):
        total_stake = mk_read_only_call(
            self.__config,
            self.__config.audit_contract.functions.totalStakedFor(self.__config.account))
        return total_stake

    def __stake(self, stake):
        return TestEscrow.__safe_transact(
            self.__config.audit_contract.functions.stake(stake),
            {"from": self.__config.account}
        )


if __name__ == '__main__':
    unittest.main()
