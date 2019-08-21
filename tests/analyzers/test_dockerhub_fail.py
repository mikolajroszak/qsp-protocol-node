####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Tests invocation of the analyzer tool.
"""
import unittest

from tempfile import TemporaryDirectory
from random import random
from helpers.resource import project_root
from helpers.resource import resource_uri
from helpers.qsp_test import QSPTest
from audit import Analyzer, Wrapper
from utils.io import fetch_file
from subprocess import CalledProcessError


class TestAnalyzerDockerhubFail(QSPTest):
    """
    Asserts different properties over analyzers when dockerhub image download fails.
    """

    @staticmethod
    def __new_analyzer(storage_dir, timeout_sec=60, prefetch=False):
        faulty_wrapper = Wrapper(
            wrappers_dir="{0}/tests/resources/wrappers".format(project_root()),
            analyzer_name="mythril",
            args="",
            storage_dir=storage_dir,
            timeout_sec=timeout_sec,
            prefetch=prefetch
        )
        return Analyzer(faulty_wrapper)

    def test_exception_on_create(self):
        """
        Tests whether a report is created upon calling the analyzer on a buggy contract. This SHOULD
        invoke dockerhub fail.
        """
        try:
            with TemporaryDirectory('mythril') as storage_dir:
                TestAnalyzerDockerhubFail.__new_analyzer(storage_dir, prefetch=True)

            self.fail("Expected an error from the wrapper pull")
        except CalledProcessError:
            # expected
            pass

    def test_report_creation(self):
        """
        Tests whether a report is created upon calling the analyzer on a buggy contract. This SHOULD
        invoke dockerhub fail.
        """
        with TemporaryDirectory('mythril') as storage_dir:
            analyzer = TestAnalyzerDockerhubFail.__new_analyzer(storage_dir)

            buggy_contract = fetch_file(resource_uri("DAOBug.sol"))
            request_id = 15
            report = analyzer.check(buggy_contract, request_id, "DAOBug.sol")

        # Asserts some result produced
        self.assertTrue(report)

        self.assertTrue(report['status'], 'error')

        self.assertEquals(2, len(report['trace']))
        self.assertEquals(1, len(report['errors']))
        msg = "Error response from daemon: pull access denied for qspprotocol/" \
              "does-not-exist-0.4.25, repository does not exist or may require 'docker login'\n"
        self.assertEquals(msg, report['errors'][0])

    def test_report_creation_once(self):
        """
        Tests whether a report is created upon calling the analyzer on a buggy contract. This SHOULD
        invoke dockerhub fail.
        """
        with TemporaryDirectory('mythril') as storage_dir:
            analyzer = TestAnalyzerDockerhubFail.__new_analyzer(storage_dir)

            open(analyzer.wrapper.storage_dir + "/.once", 'a').close()

            buggy_contract = fetch_file(resource_uri("DAOBug.sol"))
            request_id = 15
            report = analyzer.check(buggy_contract, request_id, "DAOBug.sol")

        # Asserts some result produced
        self.assertTrue(report)

        self.assertTrue(report['status'], 'error')
        self.assertTrue(len(report['trace']) >= 9)
        self.assertEquals(3, len(report['errors']))
        msg = "docker: Error response from daemon: pull access denied for qspprotocol/" \
              "does-not-exist-0.4.25, repository does not exist or may require 'docker login'.\n"
        self.assertEquals(msg, report['errors'][1])

    def test_file_not_found(self):
        """
        Tests whether an exception is raised upon calling the analyzer on a non-existent file. The
        pre-check happens without dockerhub invocation so this should not produce an error.
        """

        no_file = str(random()) + ".sol"

        with TemporaryDirectory('mythril') as storage_dir:
            analyzer = TestAnalyzerDockerhubFail.__new_analyzer(storage_dir)
            request_id = 15
            report = analyzer.check(no_file, request_id, no_file)

        self.assertTrue(report['status'], 'error')

        self.assertTrue(len(report['errors']) > 0)
        self.assertEquals(2, len(report['trace']))
        msg = "Error response from daemon: pull access denied for qspprotocol/" \
              "does-not-exist-0.4.25, repository does not exist or may require 'docker login'\n"
        self.assertEquals(msg, report['errors'][0])

    def test_file_not_found_once(self):
        """
        Tests whether an exception is raised upon calling the analyzer on a non-existent file. The
        pre-check happens without dockerhub invocation so this should not produce an error.
        """

        no_file = str(random()) + ".sol"

        with TemporaryDirectory('mythril') as storage_dir:
            analyzer = TestAnalyzerDockerhubFail.__new_analyzer(storage_dir)
            open(analyzer.wrapper.storage_dir + "/.once", 'a').close()
            request_id = 15
            report = analyzer.check(no_file, request_id, no_file)

        self.assertTrue(report['status'], 'error')

        self.assertTrue(len(report['errors']) > 0)
        self.assertEquals(6, len(report['trace']))
        self.assertTrue(
            "No such file or directory" in ''.join(err + '\n' for err in report['errors']))

    def test_old_pragma(self):
        """
        Tests whether an exception is raised upon calling the analyzer with a contract locking an
        old version of Solidity. The compilation is checked before analyzer image download only on
        the audit level, not on the analyzer level, so this SHOULD invoke dockerhub fail.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld.sol"))

        with TemporaryDirectory('mythril') as storage_dir:
            analyzer = TestAnalyzerDockerhubFail.__new_analyzer(storage_dir)
            request_id = 15
            report = analyzer.check(old_contract, request_id, "DAOBugOld.sol")

        # Asserts some result produced
        self.assertTrue(report)

        self.assertTrue(report['status'], 'error')
        self.assertEquals(2, len(report['trace']))
        self.assertEquals(1, len(report['errors']))
        msg = "Error response from daemon: pull access denied for qspprotocol/" \
              "does-not-exist-0.4.25, repository does not exist or may require 'docker login'\n"
        self.assertEquals(msg, report['errors'][0])

    def test_old_pragma_with_caret(self):
        """
        Tests whether an exception is raised upon calling the analyzer with a contract locking an
        old version of Solidity. This SHOULD invoke dockerhub fail.
        """

        old_contract = fetch_file(resource_uri("DAOBugOld-Caret.sol"))

        with TemporaryDirectory('mythril') as storage_dir:
            analyzer = TestAnalyzerDockerhubFail.__new_analyzer(storage_dir)
            request_id = 15
            report = analyzer.check(old_contract, request_id, "DAOBugOld-Caret.sol")

        self.assertTrue(report['status'], 'error')
        self.assertEquals(2, len(report['trace']))
        self.assertEquals(1, len(report['errors']))
        msg = "Error response from daemon: pull access denied for qspprotocol/" \
              "does-not-exist-0.4.25, repository does not exist or may require 'docker login'\n"
        self.assertEquals(msg, report['errors'][0])


if __name__ == '__main__':
    unittest.main()
