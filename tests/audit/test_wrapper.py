####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import os

from helpers.resource import (
    resource_uri
)
from helpers.qsp_test import QSPTest

from config import ConfigFactory


class TestWrapper(QSPTest):
    __MYTHRIL_METADATA = {'name': 'mythril',
                          'version': '9a5c1ad864df66e8cfb6ac1c283bab6f8fb25ebef0bf98405daaa04616e44316',
                          'vulnerabilities_checked': {'Call data forwarded with delegatecall()': {
                              'type': 'delegate_call_to_untrusted_contract'},
                              'Dependence on predictable environment variable': {
                                  'type': 'dependence_on_environment_variable'},
                              'Call to a user-supplied address': {
                                  'type': 'delegate_call_to_untrusted_contract'},
                              'Use of tx.origin': {
                                  'type': 'tx_origin_usage'},
                              'Ether send': {
                                  'type': 'unprotected_ether_withdrawal'},
                              'Exception state': {
                                  'type': 'exception_state'},
                              'Message call to external contract': {
                                  'type': 'call_to_external_contract'},
                              'State change after external call': {
                                  'type': 'reentrancy'},
                              'Integer Overflow': {
                                  'type': 'integer_overflow'},
                              'Integer Underflow': {
                                  'type': 'integer_underflow'},
                              'Multiple Calls': {'type': 'multiple_calls'},
                              'Unchecked SUICIDE': {
                                  'type': 'unprotected_self_destruct'},
                              'Transaction order dependence': {
                                  'type': 'transaction_order_dependency'},
                              'Unchecked CALL return value': {
                                  'type': 'unchecked_call_return_value'},
                              'Unknown': {'type': 'other'}},
                          'command': 'docker run --rm -v /tmp/.mythril/25:/shared/ -i qspprotocol/mythril-0.4.25@sha256:9a5c1ad864df66e8cfb6ac1c283bab6f8fb25ebef0bf98405daaa04616e44316  -o json -x /shared/x'}

    __SECURIFY_METADATA = {'name': 'securify',
                           'version': '16e13ac1bfc7935ca16422b9949d9a9567231fe01c09576275f6caa46d9cf8b4',
                           'vulnerabilities_checked': {
                               'MissingInputValidation': {'type': 'missing_input_validation'},
                               'LockedEther': {'type': 'locked_ether'},
                               'UnrestrictedWrite': {'type': 'unprotected_state_manipulation'},
                               'UnrestrictedEtherFlow': {'type': 'unprotected_ether_withdrawal'},
                               'UnhandledException': {'type': 'exception_state'},
                               'DAO': {'type': 'reentrancy'},
                               'DAOConstantGas': {'type': 'reentrancy'},
                               'TODReceiver': {'type': 'transaction_order_dependency'},
                               'TODTransfer': {'type': 'transaction_order_dependency'},
                               'TODAmount': {'type': 'transaction_order_dependency'},
                               'MissingInputValidationTP': {
                                   'type': 'missing_input_validation_true_positive'},
                               'LockedEtherTP': {'type': 'locked_ether_true_positive'},
                               'UnrestrictedWriteTP': {
                                   'type': 'unprotected_state_manipulation_true_positive'},
                               'UnrestrictedEtherFlowTP': {
                                   'type': 'unprotected_ether_withdrawal_true_positive'},
                               'UnhandledExceptionTP': {'type': 'exception_state_true_positive'},
                               'DAOTP': {'type': 'reentrancy_true_positive'},
                               'DAOConstantGasTP': {'type': 'reentrancy_true_positive'},
                               'TODReceiverTP': {
                                   'type': 'transaction_order_dependency_true_positive'},
                               'TODTransferTP': {
                                   'type': 'transaction_order_dependency_true_positive'},
                               'TODAmountTP': {
                                   'type': 'transaction_order_dependency_true_positive'},
                               'SecurifyBug': {'type': 'securify_bug'},
                               'Unknown': {'type': 'other'}},
                           'command': 'docker run --rm -v /tmp/.securify/37:/shared/ -i qspprotocol/securify-0.4.25@sha256:16e13ac1bfc7935ca16422b9949d9a9567231fe01c09576275f6caa46d9cf8b4  -fs /shared/x'}

    @classmethod
    def fetch_config(cls):
        # create config from file, the contract is not provided and will be injected separately
        config_file_uri = resource_uri("test_config.yaml")
        config = ConfigFactory.create_from_file(config_file_uri,
                                                os.getenv("QSP_ENV", default="dev"),
                                                validate_contract_settings=False)
        return config

    def test_get_metadata(self):
        """
        Checks that metadata is loaded correctly
        """
        config = TestWrapper.fetch_config()
        data = []
        for meta in [self.__MYTHRIL_METADATA, self.__SECURIFY_METADATA]:
            start = meta["command"].find("-v /tmp/.") + len("-v /tmp/.")
            end = meta["command"].find("shared/ -i qspprotocol")
            meta["command"] = meta["command"][0:start] + meta["command"][end:]
            data += [meta]

        for analyzer in config.analyzers:
            meta = analyzer.wrapper.get_metadata("x", 1, "x")
            self.assertNotEqual(-1, meta["command"].find(analyzer.wrapper.storage_dir))
            start = meta["command"].find("-v /tmp/.") + len("-v /tmp/.")
            end = meta["command"].find("shared/ -i qspprotocol")
            meta["command"] = meta["command"][0:start] + meta["command"][end:]
            self.assertTrue(meta in data)
