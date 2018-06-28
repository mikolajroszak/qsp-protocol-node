"""
Tests invocation of the analyzer tool.
"""
import unittest

from random import random
from helpers.resource import project_root
from helpers.resource import resource_uri
from structlog import getLogger
from audit import Analyzer, Wrapper
from utils.io import fetch_file


class TestAnalyzerOyente(unittest.TestCase):
    """
    Asserts different properties over Analyzer objects.
    """

    @staticmethod
    def __new_analyzer(storage_dir="/tmp", timeout_sec=60):
        logger = getLogger("test")
        oyente_wrapper = Wrapper(
            wrappers_dir="{0}/analyzers/wrappers".format(project_root()),
            analyzer_name="oyente",
            args="",
            storage_dir=storage_dir,
            timeout_sec=timeout_sec,
            logger=logger

        )
        return Analyzer(oyente_wrapper, getLogger("test"))

    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer
        on a buggy contract
        """
        analyzer = TestAnalyzerOyente.__new_analyzer()

        buggy_contract = fetch_file(resource_uri("DAOBug.sol"))
        request_id = 15
        report = analyzer.check(buggy_contract, request_id)

        # Asserts some result produced
        self.assertTrue(report)

        import json
        print(json.dumps(report, indent=2))

        # Asserts result is success
        self.assertTrue(report['status'], 'success')
        self.assertIsNotNone(report['potential_vulnerabilities'])

    def test_file_not_found(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        on a non-existent file
        """

        no_file = str(random()) + ".sol"
        analyzer = TestAnalyzerOyente.__new_analyzer()
        request_id = 15
        report = analyzer.check(no_file, request_id)

        self.assertTrue(report['status'], 'error')

    def test_old_pragma(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld.sol"))
        analyzer = TestAnalyzerOyente.__new_analyzer()
        request_id = 15
        report = analyzer.check(old_contract, request_id)

        self.assertTrue(report['status'], 'error')

    def test_old_pragma_with_caret(self):
        """
        Tests whether no exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity with caret.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld-Caret.sol"))
        analyzer = TestAnalyzerOyente.__new_analyzer()
        request_id = 15
        report = analyzer.check(old_contract, request_id)

        self.assertTrue(report['status'], 'success')


if __name__ == '__main__':
    unittest.main()
