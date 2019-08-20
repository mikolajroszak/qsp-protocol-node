####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Tests invocation of the analyzer tool.
"""
import json
import unittest

from random import random
from time import time
from helpers.resource import project_root
from helpers.resource import resource_uri
from helpers.qsp_test import QSPTest
from audit import Analyzer, Wrapper
from utils.io import fetch_file


class TestAnalyzerMythril(QSPTest):
    """
    Asserts different properties over Analyzer objects.
    """

    @staticmethod
    def __new_analyzer(timeout_sec=600):
        mythril_wrapper = Wrapper(
            wrappers_dir="{0}/plugins/analyzers/wrappers".format(project_root()),
            analyzer_name="mythril",
            args="",
            storage_dir="/tmp/{}{}".format(time(), random()),
            timeout_sec=timeout_sec,
        )
        return Analyzer(mythril_wrapper)

    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer
        on a buggy contract
        """
        analyzer = TestAnalyzerMythril.__new_analyzer()

        buggy_contract = fetch_file(resource_uri("DAOBug.sol"))
        request_id = 15
        report = analyzer.check(buggy_contract, request_id, "DAOBug.sol")

        # Asserts some result produced
        self.assertTrue(report)

        print(json.dumps(report, indent=2))

        # Asserts result is success
        self.assertTrue(report['status'], 'success')
        self.assertIsNotNone(report['potential_vulnerabilities'])
        self.assertEquals(3, len(report['potential_vulnerabilities']))

    def test_file_not_found(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        on a non-existent file
        """

        no_file = str(random()) + ".sol"
        analyzer = TestAnalyzerMythril.__new_analyzer()
        request_id = 15
        report = analyzer.check(no_file, request_id, no_file)

        self.assertTrue(report['status'], 'error')

        self.assertTrue(len(report['errors']) > 0)
        self.assertTrue(len(report['trace']) >= 9)
        self.assertTrue("No such file or directory" in ''.join(err + '\n' for err in report['errors']))

    def test_old_pragma(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld.sol"))
        analyzer = TestAnalyzerMythril.__new_analyzer()
        request_id = 15
        report = analyzer.check(old_contract, request_id, "DAOBugOld.sol")
        self.assertTrue(report['status'], 'error')

        self.assertTrue(len(report['errors']) > 0)
        self.assertTrue(len(report['trace']) >= 12)
        self.assertTrue("Error: Source file requires different compiler version" in ''.join(err + '\n' for err in report['errors']))

    def test_old_pragma_with_caret(self):
        """
        Tests whether no exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity with caret.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld-Caret.sol"))
        analyzer = TestAnalyzerMythril.__new_analyzer()
        request_id = 15
        report = analyzer.check(old_contract, request_id, "DAOBugOld-Caret.sol")

        self.assertTrue(report['status'], 'success')
        self.assertEquals(3, len(report['potential_vulnerabilities']))

    def test_get_metadata(self):
        analyzer = TestAnalyzerMythril.__new_analyzer()
        metadata = analyzer.get_metadata("x", 1, "x")
        self.assertTrue("name" in metadata.keys())
        self.assertTrue("version" in metadata.keys())
        self.assertTrue("vulnerabilities_checked" in metadata.keys())
        self.assertTrue("command" in metadata.keys())


if __name__ == '__main__':
    unittest.main()
