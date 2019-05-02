####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from helpers.resource import (
    fetch_config
)
from helpers.qsp_test import QSPTest


class TestWrapper(QSPTest):
    __MYTHRIL_METADATA = {'name': 'mythril',
                          'version': 'cee3a3b4eaf18ffb142294851ec3c75025a274d50611f60f934e9995b500cd40',
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
                          'command': 'docker run --rm -v /tmp/.mythril/25:/shared/ -i qspprotocol/mythril-usolc@sha256:cee3a3b4eaf18ffb142294851ec3c75025a274d50611f60f934e9995b500cd40  -o json -x /shared/x'}

    __SECURIFY_METADATA = {'name': 'securify',
                           'version': '25589280694d5c0e669bc1de086de43efc043e03e7863703a8e35052435c66cc',
                           'vulnerabilities_checked': {
                               'MissingInputValidation': {'type': 'missing_input_validation'},
                               'LockedEther': {'type': 'locked_ether'},
                               'UnrestrictedWrite': {'type': 'unprotected_state_manipulation'},
                               'UnrestrictedEtherFlow': {'type': 'unprotected_ether_withdrawal'},
                               'UnhandledException': {'type': 'unchecked_call_return_value'},
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
                               'UnhandledExceptionTP': {'type': 'unchecked_call_return_value_true_positive'},
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
                           'command': 'docker run --rm -v /tmp/.securify/37:/shared/ -i qspprotocol/securify-usolc@sha256:25589280694d5c0e669bc1de086de43efc043e03e7863703a8e35052435c66cc  -fs /shared/x'}

    def test_get_metadata(self):
        """
        Checks that metadata is loaded correctly
        """
        config = fetch_config()
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
