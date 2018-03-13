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

    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer
        on a buggy contract
        """
        analyzer = Analyzer("./oyente/oyente/oyente.py -j -s ${input}")

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
        analyzer = Analyzer("./oyente/oyente/oyente.py -j -s ${input}")

        report = analyzer.check(inexistent_file, "${input}.json", "123")

        self.assertTrue(report['status'], 'error')


if __name__ == '__main__':
    unittest.main()
