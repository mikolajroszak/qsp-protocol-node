####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Tests invocation of the analyzer tool.
"""
import json
import unittest

from random import random
from helpers.resource import project_root
from helpers.resource import resource_uri
from structlog import getLogger
from audit import Analyzer, Wrapper
from utils.io import fetch_file


class TestAnalyzerMythril(unittest.TestCase):
    """
    Asserts different properties over Analyzer objects.
    """

    @staticmethod
    def __new_analyzer(storage_dir="/tmp", timeout_sec=60):
        logger = getLogger("test")
        mythril_wrapper = Wrapper(
            wrappers_dir="{0}/analyzers/wrappers".format(project_root()),
            analyzer_name="mythril",
            args="",
            storage_dir=storage_dir,
            timeout_sec=timeout_sec,
            logger=logger

        )
        return Analyzer(mythril_wrapper, getLogger("test"))

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
        self.assertEquals(3, report['count_potential_vulnerabilities'])

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
        self.assertEquals(1, len(report['errors']))
        self.assertEquals(4, len(report['trace']))
        self.assertTrue("No such file or directory" in report['errors'][0])

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
        self.assertEquals(1, len(report['errors']))
        self.assertEquals(7, len(report['trace']))
        self.assertTrue("Error: Source file requires different compiler version" in report['errors'][0])

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
        self.assertEquals(3, report['count_potential_vulnerabilities'])


if __name__ == '__main__':
    unittest.main()
