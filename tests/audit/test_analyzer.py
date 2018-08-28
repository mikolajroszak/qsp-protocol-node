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
import unittest
import random

from audit import Analyzer
from audit import Wrapper
from utils.io import fetch_file
from helpers.resource import project_root
from helpers.resource import resource_uri
from structlog import getLogger


class TestOyenteAnalyzer(unittest.TestCase):
    """
    Asserts different properties over Analyzer objects.
    """

    @staticmethod
    def __new_oyente_analyzer(args="", storage_dir="/tmp", timeout_sec=60):
        logger = getLogger("test")
        oyente_wrapper = Wrapper(
            wrappers_dir="{0}/analyzers/wrappers".format(project_root()),
            analyzer_name="oyente",
            args="-ce",
            storage_dir=storage_dir,
            timeout_sec=timeout_sec,
            logger=logger,
        )
        return Analyzer(oyente_wrapper, logger)

    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer
        on a buggy contract
        """
        analyzer = TestOyenteAnalyzer.__new_oyente_analyzer()

        buggy_contract = fetch_file(resource_uri("DAOBug.sol"))
        request_id = random.randrange(1, 100)
        report = analyzer.check(buggy_contract, request_id, "DAOBug.sol")

        # Asserts some result produced
        self.assertTrue(report)

        import json
        print(json.dumps(report, indent=2))

        # Asserts result is success
        self.assertTrue(report['status'], 'success')
        self.assertTrue(report['potential_vulnerabilities'] is not None)

    def test_file_not_found(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        on a non-inexistent file
        """

        filename_prefix = str(random.randrange(1, 100))
        inexistent_file = "{0}.sol".format(filename_prefix)
        analyzer = TestOyenteAnalyzer.__new_oyente_analyzer()

        request_id = random.randrange(1, 100)
        report = analyzer.check(inexistent_file, request_id, inexistent_file)

        self.assertTrue(report['status'], 'error')

    def test_old_pragma(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld.sol"))
        analyzer = TestOyenteAnalyzer.__new_oyente_analyzer()

        request_id = random.randrange(1, 100)
        report = analyzer.check(old_contract, request_id, "DAOBugOld.sol")

        self.assertTrue(report['status'], 'error')

    def test_old_pragma_with_carot(self):
        """
        Tests whether an exception is raised upon calling the analyzer
        with a contract locking an old version of Solidity.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld-Caret.sol"))
        analyzer = TestOyenteAnalyzer.__new_oyente_analyzer()

        request_id = random.randrange(1, 100)
        report = analyzer.check(old_contract, request_id, "DAOBugOld-Caret.sol")

        self.assertTrue(report['status'], 'success')


if __name__ == '__main__':
    unittest.main()
