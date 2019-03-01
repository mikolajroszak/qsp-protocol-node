####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from audit import PerformAuditThread
from helpers.qsp_test import QSPTest
from helpers.resource import (
    fetch_config,
    resource_uri,
)
from utils.io import fetch_file
from timeout_decorator import timeout


class TestPerformAuditThread(QSPTest):

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__config = fetch_config()
        self.__thread = PerformAuditThread(self.__config)

    def test_init(self):
        self.assertEqual(self.__config, self.__thread.config)

    def test_stop(self):
        config = fetch_config()
        thread = PerformAuditThread(config)
        thread.stop()
        self.assertFalse(thread.exec)

    @timeout(300, timeout_exception=StopIteration)
    def test_analyzer_produces_metadata_for_errors(self):
        """
        Tests that analyzers produce their metadata even when failure occurs
        """
        buggy_contract = resource_uri("BasicToken.sol")
        buggy_contract_file = fetch_file(buggy_contract)
        # directly calling this function to avoid compilation checks;
        # this will cause error states for the analyzers
        report = self.__thread.get_audit_report_from_analyzers(buggy_contract_file,
                                                               "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                                                               buggy_contract,
                                                               1)
        self.compare_json(report, "reports/BasicTokenErrorWithMetadata.json", json_loaded=True)
