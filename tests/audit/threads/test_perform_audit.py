####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
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


class WrapperMock:
    @property
    def analyzer_name(self):
        return "Mock Analyzer"


class TestPerformAuditThread(QSPTest):

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__config = fetch_config(inject_contract=True)
        self.__thread = PerformAuditThread(self.__config)

    def test_init(self):
        self.assertEqual(self.__config, self.__thread.config)

    def test_stop(self):
        config = fetch_config(inject_contract=True)
        thread = PerformAuditThread(config)
        thread.stop()
        self.assertFalse(thread.exec)

    def test_compute_audit_result_all_timeouts(self):
        statuses = ["timeout", "timeout", "timeout"]
        self.__check_audit_result(statuses,
                                  self.__thread._PerformAuditThread__AUDIT_STATE_ERROR,
                                  self.__thread._PerformAuditThread__AUDIT_STATUS_ERROR)

    def test_compute_audit_result_one_timeout(self):
        statuses = ["timeout", "success", "success"]
        self.__check_audit_result(statuses,
                                  self.__thread._PerformAuditThread__AUDIT_STATE_SUCCESS,
                                  self.__thread._PerformAuditThread__AUDIT_STATUS_SUCCESS)

    def test_compute_audit_result_error(self):
        statuses = ["timeout", "error", "success"]
        self.__check_audit_result(statuses,
                                  self.__thread._PerformAuditThread__AUDIT_STATE_ERROR,
                                  self.__thread._PerformAuditThread__AUDIT_STATUS_ERROR)

    def test_compute_audit_result_all_success(self):
        statuses = ["success", "success", "success"]
        self.__check_audit_result(statuses,
                                  self.__thread._PerformAuditThread__AUDIT_STATE_SUCCESS,
                                  self.__thread._PerformAuditThread__AUDIT_STATUS_SUCCESS)

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

    def __check_audit_result(self, statuses, expected_state, expected_status):
        wrappers = [WrapperMock() for _ in statuses]
        local_reports = [{"status": i} for i in statuses]
        state, status = self.__thread._PerformAuditThread__compute_audit_result(wrappers,
                                                                                local_reports)
        self.assertEqual(expected_state, state)
        self.assertEqual(expected_status, status)
