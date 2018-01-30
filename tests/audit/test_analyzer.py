"""
Tests invocation of the analyzer tool.
"""
import unittest
from random import random
from audit import Analyzer

class TestAnalyzer(unittest.TestCase):
    """
    Asserts different properties over Analyzer objects.
    """
    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer
        on a buggy contract
        """
        analyzer = Analyzer ("oyente -j -s ${input}", "0.4.17")
        result = analyzer.check("resources/DAOBug.sol", "${input}.json")
        self.assertTrue(result)

    def test_file_not_found(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        on a non-inexistent file
        """
        inexistent_file = str(random()) + ".sol"
        analyzer = Analyzer ("oyente -j -s ${input}", "0.4.17")

        with self.assertRaises(Exception):
            analyzer.check(inexistent_file, "${input}.json")

    if __name__ == '__main__':
        unittest.main()

