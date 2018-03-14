"""
Tests invocation of the analyzer tool.
"""
import unittest
from random import random
from audit import Analyzer, AnalyzerRunException

from utils.io import fetch_file
from helpers.resource import resource_uri


class TestAnalyzer(unittest.TestCase):
    """
    Asserts different properties over Analyzer objects.
    """

    __ANALYZER_CMD_TEMPLATE = "./oyente/oyente/oyente.py -j -s ${input}"

    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer
        on a buggy contract
        """
        analyzer = Analyzer(TestAnalyzer.__ANALYZER_CMD_TEMPLATE)

        buggy_contract = fetch_file(resource_uri("DAOBug.sol"))
        report = analyzer.check(buggy_contract, "${input}.json", "123")

        # Asserts some result produced
        self.assertTrue(report)

        # Asserts result is success
        self.assertTrue(report['status'], 'success')
        self.assertTrue(report['result'] is not None)

    def test_file_not_found(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        on a non-inexistent file
        """

        inexistent_file = str(random()) + ".sol"
        analyzer = Analyzer(TestAnalyzer.__ANALYZER_CMD_TEMPLATE)

        report = analyzer.check(inexistent_file, "${input}.json", "123")

        self.assertTrue(report['status'], 'error')

    def test_old_pragma(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld.sol"))
        analyzer = Analyzer(TestAnalyzer.__ANALYZER_CMD_TEMPLATE)

        report = analyzer.check(old_contract, "${input}.json", "123")

        self.assertTrue(report['status'], 'error')
        print("===> report is " + str(report))


if __name__ == '__main__':
    unittest.main()
