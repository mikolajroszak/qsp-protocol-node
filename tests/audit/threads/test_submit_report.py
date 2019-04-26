####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from unittest import mock
from unittest.mock import MagicMock

from audit import SubmitReportThread
from audit.report_processing import ReportEncoder
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config, resource_uri
from utils.io import fetch_file, load_json


class TestSubmitReportThread(QSPTest):

    def setUp(self):
        """
        Starts the execution of the QSP audit node as a separate thread.
        """
        self.__config = fetch_config(inject_contract=True)
        self.__submit_thread = SubmitReportThread(self.__config)

    def test_get_report_in_blockchain_no_exception(self):
        """
        Tests whether calling the smart contract to get a report in the blockchain works.
        """
        self.__submit_thread._SubmitReportThread__get_report_in_blockchain(0)

    def test_submit_police_report(self):
        """
        Tests whether submitting police report works.
        """
        tx_hash = self.__submit_thread._SubmitReportThread__submit_police_report(1, "", True)
        self.assertIsNotNone(tx_hash)
        with mock.patch('audit.threads.submit_report_thread.send_signed_transaction',
                        return_value="hash"):
            tx_hash = self.__submit_thread._SubmitReportThread__submit_police_report(1, "", True)
            self.assertEquals(tx_hash, "hash")

    def test_encoding_to_get_report_in_blockchain(self):
        compressed_report_bytes = b' \x03\x90\xb5U\xf2\xefS\'\xe1\x89`\x01\xd8tb\xe2\xe6\x9d\xa3\xda\xac\xe1\x8c\xb7\xb6\x0f"1$\x93\xa9\xc4\xf9\x05\x00\x0f\x0c\x00\x0f\r\x00\x0f\x05\x00\x13\x03\x00\x0f\x07\x00\x0f\x1a\x00\x0f\x15\x00\x06\x12\x00\x0e\x12\x00\n'
        expected_compressed_report_hex = '200390b555f2ef5327e1896001d87462e2e69da3daace18cb7b60f22312493a9c4f905000f0c000f0d000f05001303000f07000f1a000f15000612000e12000a'
        with mock.patch('audit.threads.submit_report_thread.mk_read_only_call',
                        return_value=compressed_report_bytes):
            hex_compressed_report = self.__submit_thread._SubmitReportThread__get_report_in_blockchain(
                request_id=1
            )
            self.assertEquals(hex_compressed_report, expected_compressed_report_hex)

    def __test_auditor_report_correctness(self, auditor_compressed_report, police_report,
                                          deemed_correct):
        self.__submit_thread._SubmitReportThread__get_report_in_blockchain = MagicMock()
        self.__submit_thread._SubmitReportThread__get_report_in_blockchain.return_value = \
            auditor_compressed_report
        is_deemed_correct = self.__submit_thread._SubmitReportThread__is_report_deemed_correct(
            1,
            police_report
        )
        self.assertEquals(is_deemed_correct, deemed_correct)

    def test_is_report_deemed_correct_for_empty_police_report(self):
        # Get the contract_hash from the DAOBug report
        full_report = self.__load_report("reports/DAOBug.json")
        contract_hash = full_report.get('contract_hash', "")

        # Update the police report with the correct hash
        police_report = self.__load_report("reports/Empty.json")
        police_report["status"] = "success"
        police_report['contract_hash'] = contract_hash

        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBug.json"),
            police_report=police_report,
            deemed_correct=True
        )

    def test_is_report_deemed_incorrect_for_different_contract_hashes(self):
        police_report = self.__load_report("reports/DAOBug.json")
        police_report[
            'contract_hash'] = "1111111111111111111111111111111111111111111111111111111111111111"

        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBug.json"),
            police_report=police_report,
            deemed_correct=False
        )

    def test_is_report_deemed_incorrect_for_disjoint_reports(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/Empty.json"),
            police_report=self.__load_report("reports/DAOBug.json"),
            deemed_correct=False
        )

    def test_is_report_deemed_correct_for_equal_reports(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBug.json"),
            police_report=self.__load_report("reports/DAOBug.json"),
            deemed_correct=True
        )

    def test_is_report_deemed_correct_for_report_under_threshold(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBugIncomplete.json"),
            police_report=self.__load_report("reports/DAOBug.json"),
            deemed_correct=False
        )

    def test_is_report_deemed_correct_in_case_of_no_vulnerabilities(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/Empty.json"),
            police_report=self.__load_report("reports/Empty.json"),
            deemed_correct=True
        )

    def test_is_report_deemed_correct_in_case_of_incorrect_encoding(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=b'garbage',
            police_report=resource_uri("reports/DAOBug.json"),
            deemed_correct=False
        )

    def test_is_report_deemed_correct_in_case_error_statuses(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/Empty.json"),
            police_report=self.__load_report("reports/Empty.json"),
            deemed_correct=True
        )

    def test_is_report_deemed_correct_in_case_different_statuses(self):
        police_report = self.__load_report("reports/Empty.json")
        # switch the status to success
        police_report["status"] = "success"

        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/Empty.json"),
            police_report=police_report,
            deemed_correct=False
        )

    def __compressed_report(self, report_file_path):
        full_report = self.__load_report(report_file_path)
        request_id = full_report['request_id']

        encoder = ReportEncoder()
        return encoder.compress_report(full_report, request_id)

    def __load_report(self, report_file_path):
        return load_json(fetch_file(resource_uri(report_file_path)))
