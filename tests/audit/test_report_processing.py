####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Tests report compression and decoding
"""
import unittest
import os
import json
from pprint import pprint

import jsonschema
from deepdiff import DeepDiff

import audit.report_processing

from audit.report_processing import ReportEncoder
from audit.report_processing import ReportFormattingException
from helpers.resource import resource_uri
from helpers.qsp_test import QSPTest
from utils.io import load_json, fetch_file


class TestReportProcessing(QSPTest):
    """
    Tests correctness of encoding and decoding functions
    """

    def setUp(self):
        self.__encoder = audit.report_processing.ReportEncoder()

    def __compare_json(self, actual_json, expected_json):
        diff = DeepDiff(
            actual_json,
            expected_json,
            exclude_paths={
                "root['version']"
            }
        )
        self.assertEqual(diff, {})

    @staticmethod
    def mock_report(version=None,
                    audit_state=None,
                    status=None,
                    contract_hash=None,
                    vulnerabilities=None,
                    vulnerabilities_count=0):
        """
        Creates a JSON-formatted report.
        vulnerabilities must be a list of tuples of the form: (type, start_line, end_line).
        """
        if version is None:
            version = "0.0.0"
        if audit_state is None:
            audit_state = ReportEncoder._ReportEncoder__AUDIT_STATE_SUCCESS
        if status is None:
            status = ReportEncoder._ReportEncoder__AUDIT_STATUS_ERROR
        if contract_hash is None:
            contract_hash = "0" * 64
        if vulnerabilities is None:
            vulnerabilities = [("reentrancy", i + 1, i + 1) for i in range(vulnerabilities_count)]
        report = {
            "version": version,
            "audit_state": audit_state,
            "status": status,
            "contract_hash": contract_hash,
        }
        potential_vulnerabilities = []
        for vulnerability_type, start_line, end_line in vulnerabilities:
            potential_vulnerabilities.append(
                {
                    "type": vulnerability_type,
                    "instances": [
                        {
                            "start_line": start_line,
                            "end_line": end_line,
                        }
                    ]
                }
            )

        analyzers_reports = [
            {
                "potential_vulnerabilities": potential_vulnerabilities
            }
        ]

        report["analyzers_reports"] = analyzers_reports
        return report

    @staticmethod
    def validate_json(report):
        """
        Validate that the report conforms to the schema.
        """
        try:
            file_path = os.path.realpath(__file__)
            schema_file = '{0}/../../analyzers/schema/analyzer_integration.json'.format(
                os.path.dirname(file_path))
            with open(schema_file) as schema_data:
                schema = json.load(schema_data)
            jsonschema.validate(report, schema)
            return True
        except jsonschema.ValidationError as e:
            pprint(report)
            print(e)
            return False

    def compress_report(self, report):
        """
        Compresses the JSON report.
        """
        return self.__encoder.compress_report(report, 1)

    def decode_report(self, report):
        """
        Decodes the hexstring report.
        """
        report = self.__encoder.decode_report(report, 1)
        self.assertTrue(TestReportProcessing.validate_json(report))
        return report

    def test_decimal_to_bitstring(self):
        """
        Ensures that decimals are correctly encoded to bitstrings.
        """
        self.assertEqual(self.__encoder._ReportEncoder__to_bitstring(14, 4), "1110")
        self.assertEqual(self.__encoder._ReportEncoder__to_bitstring(14, 8), "00001110")
        self.assertEqual(self.__encoder._ReportEncoder__to_bitstring(256, 16), "0000000100000000")

    def test_hex_to_bitstring(self):
        """
        Ensures that hex is correctly encoded to bitstrings.
        """
        self.assertEqual(self.__encoder._ReportEncoder__to_bitstring("A", 4, is_hex=True), "1010")
        self.assertEqual(self.__encoder._ReportEncoder__to_bitstring("a", 4, is_hex=True), "1010")
        self.assertEqual(self.__encoder._ReportEncoder__to_bitstring("abc123",
                                                                     24,
                                                                     is_hex=True),
                         "101010111100000100100011")

    def test_bitstring_to_decimal(self):
        """
        Ensures that bitstrings are correctly converted to decimals.
        """
        self.assertEqual(self.__encoder._ReportEncoder__from_bitstring("1010"), 10)
        self.assertEqual(self.__encoder._ReportEncoder__from_bitstring("1000"), 8)
        self.assertEqual(self.__encoder._ReportEncoder__from_bitstring("100001"), 33)

    def test_number_exceeds_bitstring_size(self):
        """
        Ensures that an error is raised if the number to be encoded is too large.
        """
        self.assertRaises(ReportFormattingException,
                          self.__encoder._ReportEncoder__to_bitstring, 14, 3)
        self.assertRaises(ReportFormattingException,
                          self.__encoder._ReportEncoder__to_bitstring, 1, 0)

    def test_hex_incorrect_bitstring_size(self):
        """
        Ensures that an error is raised if the hex to be encoded is too large or small.
        """
        self.assertRaises(ReportFormattingException,
                          ReportEncoder._ReportEncoder__to_bitstring, "a", 3, True)
        self.assertRaises(ReportFormattingException,
                          ReportEncoder._ReportEncoder__to_bitstring, "ab", 4, True)
        self.assertRaises(ReportFormattingException,
                          ReportEncoder._ReportEncoder__to_bitstring, "abc123", 39, True)

    def test_bitstring_to_hex(self):
        """
        Ensures that bitstrings are correctly converted to hex.
        """
        self.assertEqual(ReportEncoder._ReportEncoder__to_hex("1010"), "A")
        self.assertEqual(ReportEncoder._ReportEncoder__to_hex("101010111100000100100011"),
                         "ABC123")

    def test_buggy_bitstring_to_hex(self):
        """
        Ensures that an Exception is raised if a bitstring's length is not divisible by 4,
        or if it contains a non-hex character.
        """
        self.assertRaises(ReportFormattingException, ReportEncoder._ReportEncoder__to_hex, "101")
        self.assertRaises(ReportFormattingException,
                          ReportEncoder._ReportEncoder__to_hex, "1010101111000001001000")

    def test_version_compression(self):
        """
        Ensures that the version is compressed properly.
        """
        tests = [
            ("0.0.0", "00000000000000"),
            ("0.1.2", "00000001000010"),
            ("4.9.12", "01001001001100"),
            ("15.15.63", "11111111111111"),
        ]
        for version, expected_bitstring in tests:
            report = TestReportProcessing.mock_report(version=version)
            bitstring = ReportEncoder._ReportEncoder__encode_header_bytes(report["version"],
                                                                          report["audit_state"],
                                                                          report["status"],
                                                                          )
            version_bitstring = bitstring[:14]  # the first 14 bits in the header encode version
            self.assertEqual(version_bitstring, expected_bitstring)

    def test_version_decoding(self):
        """
        Ensures that the version is decoded properly.
        """
        tests = ["0.0.0", "0.1.2", "4.9.12", "15.15.63"]

        for version in tests:
            report = TestReportProcessing.mock_report(version=version)
            hexstring = self.compress_report(report)
            decoded_report = self.decode_report(hexstring)
            self.assertEqual(decoded_report["version"], version)

    def test_audit_state_compression(self):
        """
        Ensures that the audit_state is compressed properly.
        """
        audit_states = [
            (ReportEncoder._ReportEncoder__AUDIT_STATE_SUCCESS, "1"),
            (ReportEncoder._ReportEncoder__AUDIT_STATE_ERROR, "0"),
        ]
        for state, expected_state in audit_states:
            report = TestReportProcessing.mock_report(audit_state=state)
            bitstring = ReportEncoder._ReportEncoder__encode_header_bytes(report["version"],
                                                                          report["audit_state"],
                                                                          report["status"],
                                                                          )
            audit_state_bit = bitstring[self.__encoder._ReportEncoder__AUDIT_STATE_INDEX]
            self.assertEqual(audit_state_bit, expected_state)

    def test_buggy_audit_state_compression(self):
        """
        Ensures that compression raises an Exception if the audit_state is wrongly formatted.
        audit_state must equal 4 (success) or 5 (error).
        """
        audit_states = [0, 3, 6, "4", "5"]
        for state in audit_states:
            report = TestReportProcessing.mock_report(audit_state=state)
            self.assertRaises(ReportFormattingException,
                              self.__encoder._ReportEncoder__encode_header_bytes,
                              report["version"],
                              report["audit_state"],
                              report["status"],
                              )

    def test_audit_state_decoding(self):
        """
        Ensures that the audit_state is decoded properly.
        """
        audit_states = [
            ReportEncoder._ReportEncoder__AUDIT_STATE_SUCCESS,
            ReportEncoder._ReportEncoder__AUDIT_STATE_ERROR,
        ]

        for state in audit_states:
            report = TestReportProcessing.mock_report(audit_state=state)
            hexstring = self.compress_report(report)
            decoded_report = self.decode_report(hexstring)
            self.assertEqual(decoded_report["audit_state"], state)

    def test_status_compression(self):
        """
        Ensures that the status is compressed properly.
        """
        statuses = [("success", "1"), ("error", "0")]
        for status, expected_status in statuses:
            report = TestReportProcessing.mock_report(status=status)
            bitstring = self.__encoder._ReportEncoder__encode_header_bytes(report["version"],
                                                                           report["audit_state"],
                                                                           report["status"],
                                                                           )
            status_bit = bitstring[self.__encoder._ReportEncoder__STATUS_INDEX]
            self.assertEqual(status_bit, expected_status)

    def test_buggy_status_compression(self):
        """
        Ensures that compression raises an Exception if the status is wrongly formatted.
        status must be "success" or "error".
        """
        statuses = ["bad status", 1]
        for status in statuses:
            report = TestReportProcessing.mock_report(status=status)
            self.assertRaises(ReportFormattingException,
                              self.__encoder._ReportEncoder__encode_header_bytes,
                              report["version"],
                              report["audit_state"],
                              report["status"],
                              )

    def test_status_decoding(self):
        """
        Ensures that the status is decoded properly.
        """
        statuses = ["success", "error"]

        for status in statuses:
            report = TestReportProcessing.mock_report(status=status)
            hexstring = self.compress_report(report)
            decoded_report = self.decode_report(hexstring)
            self.assertEqual(decoded_report["status"], status)

    def test_contract_hash_compression(self):
        """
        Ensures that a contract_hash is compressed properly.
        """
        contract_hashes = [
            ("F" * 64, "1" * 256),
            ("A" * 64, "1010" * 64),
            ("12" * 32, "00010010" * 32),
        ]
        for contract_hash, expected_hash in contract_hashes:
            report = TestReportProcessing.mock_report(contract_hash=contract_hash)
            hexstring = self.compress_report(report)
            bitstring = self.__encoder._ReportEncoder__to_bitstring(hexstring, is_hex=True)

            # W504 line break after binary operator...
            # W503 line break before binary operator......
            end = self.__encoder._ReportEncoder__CONTRACT_HASH_START
            end += self.__encoder._ReportEncoder__CONTRACT_HASH_SIZE

            b_contract_hash = bitstring[
                              self.__encoder._ReportEncoder__CONTRACT_HASH_START: end]
            self.assertEqual(expected_hash, b_contract_hash)

    def test_buggy_contract_hash_compression(self):
        """
        Ensures that compression raises an Exception if the contract_hash wrongly formatted.
        """
        contract_hashes = [
            "G" * 64,  # non-hex character
            "A" * 65,  # too long
            "A" * 63,  # too short
        ]
        for contract_hash in contract_hashes:
            report = TestReportProcessing.mock_report(contract_hash=contract_hash)
            self.assertRaises(ReportFormattingException,
                              self.compress_report,
                              report,
                              )

    def test_contract_hash_decoding(self):
        """
        Ensures that a contract_hash is decoded properly.
        """
        contract_hashes = [
            "F" * 64,
            "A" * 64,
            "12" * 32,
        ]
        for contract_hash in contract_hashes:
            report = TestReportProcessing.mock_report(contract_hash=contract_hash)
            hexstring = self.compress_report(report)
            decoded_report = self.decode_report(hexstring)
            self.assertEqual(contract_hash, decoded_report["contract_hash"])

    def test_vulnerabilities_compression_and_decoding(self):
        """
        Ensures that a report with several vulnerabilities is compressed properly.
        """
        vulnerabilities_count = [1, 5, 20]
        for count in vulnerabilities_count:
            report = TestReportProcessing.mock_report(vulnerabilities_count=count)
            hexstring = self.compress_report(report)
            decoded_report = self.decode_report(hexstring)
            vulnerabilities = decoded_report["analyzers_reports"][0]["potential_vulnerabilities"]
            self.assertEqual(len(vulnerabilities[0]["instances"]), count)
            for i in range(len(vulnerabilities[0]["instances"])):
                # the encoded start_line numbers are correct
                self.assertEqual(vulnerabilities[0]["instances"][i]["start_line"], i + 1)

    def test_vulnerabilities_with_end_lines_compression_and_decoding(self):
        """
        Ensures that a report with vulnerability end_lines are compressed properly.
        """
        # order does not matter here
        type_names = list(self.__encoder._ReportEncoder__vulnerability_types)
        vulnerabilities = [(type_names[0], 1, 2),
                           (type_names[1], 3, 3),
                           (type_names[2], 4, 50),
                           (type_names[3], 5, 255)]
        report = TestReportProcessing.mock_report(vulnerabilities=vulnerabilities)
        hexstring = self.compress_report(report)
        decoded_report = self.decode_report(hexstring)
        decoded_vulnerabilities = decoded_report["analyzers_reports"][0]["potential_vulnerabilities"]
        self.assertEqual(len(vulnerabilities), len(decoded_vulnerabilities))
        for v1, v2 in zip(vulnerabilities, decoded_vulnerabilities):
            # the encoded types are correct
            self.assertEqual(v1[0], v2["type"])
            # the encoded start_line numbers are correct
            self.assertEqual(v1[1], v2["instances"][0]["start_line"])
            # the encoded end_line numbers are correct
            self.assertEqual(v1[2], v2["instances"][0]["end_line"])

    def test_compress_and_decode_full_report(self):
        """
        Ensures that a typical, complete report is compressed properly.
        """
        report = load_json(fetch_file(resource_uri("reports/DAOBug.json")))
        hexstring = self.compress_report(report)
        decoded_report = self.decode_report(hexstring)

        expected_report = load_json(fetch_file(resource_uri("reports/DAOBugDecompressed.json")))
        self.__compare_json(decoded_report, expected_report)

    def test_buggy_empty_report(self):
        """
        Ensures that an Exception is raised if an empty JSON is passed in.
        """
        self.assertRaises(Exception, self.compress_report, {})

    def test_compress_and_decode_really_large_report(self):
        """
        Tests that a report with many vulnerabilities is efficiently compressed and decoded.
        """
        COUNT = 1000
        report = TestReportProcessing.mock_report(vulnerabilities_count=COUNT)
        hexstring = self.compress_report(report)
        decoded_report = self.decode_report(hexstring)
        vulnerabilities = decoded_report["analyzers_reports"][0]["potential_vulnerabilities"]
        self.assertEqual(len(vulnerabilities[0]["instances"]), COUNT)
        for i in range(len(vulnerabilities[0]["instances"])):
            # the encoded start_line numbers are correct
            self.assertEqual(vulnerabilities[0]["instances"][i]["start_line"], i + 1)

    def test_vulnerability_types_compression_and_decoding(self):
        """
        Ensures that all vulnerability types are encoded properly.
        """
        type_bitstrings = list(self.__encoder._ReportEncoder__vulnerability_types_inverted)
        vulnerabilities = []
        for i in range(len(type_bitstrings)):
            vulnerabilities.append(
                (self.__encoder._ReportEncoder__vulnerability_types_inverted[type_bitstrings[i]],
                 i + 1,
                 i + 1)
            )
        report = TestReportProcessing.mock_report(vulnerabilities=vulnerabilities)
        hexstring = self.compress_report(report)
        decoded_report = self.decode_report(hexstring)
        decoded_vulnerabilities = decoded_report["analyzers_reports"][0]["potential_vulnerabilities"]

        for b, v in zip(type_bitstrings, decoded_vulnerabilities):
            self.assertEqual(self.__encoder._ReportEncoder__vulnerability_types_inverted[b],
                             v["type"])

    def test_buggy_vulnerability_types_compression(self):
        """
        Tests that an Exception is raised if a non-listed type is attempted to be encoded.
        """
        vulnerabilities = [("unlisted_type", 1, 2)]
        report = TestReportProcessing.mock_report(vulnerabilities=vulnerabilities)
        self.assertRaises(ReportFormattingException, self.compress_report, report)

    @staticmethod
    def __get_json(file_name, field=None):
        """
        Returns a json map from a file, optionally returning a single field
        """
        with open(file_name) as json_data:
            json_map = json.load(json_data)
            if field:
                return json_map[field]
            else:
                return json_map

    def test_types_file_matches_analyzers(self):
        """
        Ensures that the vulnerability list matches vulnerabilities from all analyzers
        """
        script_path = os.path.realpath(__file__)
        json_fstr = "{0}/../../analyzers/vulnerability_types.json"
        file_name = json_fstr.format(os.path.dirname(script_path))

        types_list = TestReportProcessing.__get_json(file_name, "vulnerabilities")

        wrappers_dir = "{0}/../../analyzers/wrappers/".format(os.path.dirname(script_path))
        wrappers = [os.path.join(wrappers_dir, w) for w in os.listdir(wrappers_dir)
                    if os.path.isdir(os.path.join(wrappers_dir, w)) and "common" not in w]

        wrapper_types = set()
        for wrapper in wrappers:
            json_fstr = "{0}/resources/vulnerabilities.json"
            file_name = json_fstr.format(wrapper)
            types_json = TestReportProcessing.__get_json(file_name)
            for name in types_json:
                wrapper_types.add(types_json[name]["type"])

        self.assertEqual(set(types_list), wrapper_types)

    def test_encode_decode_idempotence(self):
        """
        Ensures that encode(decode(report)) == encode(decode(encode(decode(report))))
        """
        report = load_json(fetch_file(resource_uri("reports/DAOBug.json")))
        decoded_report = self.decode_report(self.compress_report(report))
        twice_decoded_report = self.decode_report(self.compress_report(decoded_report))
        self.__compare_json(decoded_report, twice_decoded_report)


if __name__ == '__main__':
    unittest.main()
