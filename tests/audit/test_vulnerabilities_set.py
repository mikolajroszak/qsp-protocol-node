####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

import os
import unittest

from audit import VulnerabilitiesSet
from audit.report_processing import ReportEncoder
from helpers.resource import resource_uri, fetch_config
from utils.io import fetch_file, load_json


class TestVulnerabilitiesSet(unittest.TestCase):

    def test_create_set_from_nil_uncompressed_report(self):
        """
        Tests whether the resulting vulnerability set from a nil report
        is empty
        """
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(None), set())
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(None,), set())

    def test_create_set_from_empty_uncompressed_report(self):
        """
        Tests whether the resulting vulnerability set from an empty report
        is empty
        """
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report({}), set())
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report({}), set())

    def test_create_set_from_erroneous_uncompressed_eport(self):
        """
        Tests whether the resulting vulnerability set from an erroneous report
        is empty
        """
        incomplete_report = {
            'status': 'error'
        }
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(incomplete_report), set())
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(incomplete_report), set())

        decompressed_incomplete_report = {
            'status': 'error',
            'analyzer_reports': [
                {'analyzer': 'oyente', 'status': 'error'},
                {'analyzer': 'mythril', 'status': 'error'}
            ],
        }
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(decompressed_incomplete_report), set())
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(decompressed_incomplete_report), set())

    def test_create_set_from_uncompressed_report_with_no_vulnerabilities(self):
        decompressed_report = {
            'status': 'success',
            'analyzer_reports': [
                {'analyzer': 'oyente', 'status': 'success'},
                {'analyzer': 'mythril', 'status': 'success'}
            ],
        }
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(decompressed_report), set())
        self.assertEqual(VulnerabilitiesSet.from_uncompressed_report(decompressed_report), set())

    def test_create_set_from_uncompressed_report_with_vulnerabilities(self):
        decompressed_report = {
            'analyzers_reports': [
                {
                    'status': 'success',
                    'potential_vulnerabilities': [
                        {
                            'type': 'some-type1',
                            'instances': [
                                {'start_line': 123},
                                {'start_line': 124},
                                {'start_line': 125},
                            ]
                        },
                        {
                            'type': 'some-type2',
                            'instances': [
                                {'start_line': 245},
                                {'start_line': 246},
                                {'start_line': 247},
                            ]
                        },
                    ],
                    'analyzer': {
                        'analyzer': 'dummy1'
                    }
                },
                {
                    'status': 'success',
                    'potential_vulnerabilities': [
                        {
                            'type': 'some-type2',
                            'instances': [
                                {'start_line': 245},
                                {'start_line': 246}
                            ]
                        }
                    ],
                    'analyzer': {
                        'analyzer': 'dummy2'
                    }
                }
            ]
        }
        self.assertEqual(
            VulnerabilitiesSet.from_uncompressed_report(decompressed_report),
            {
                ('some-type1', 123),
                ('some-type1', 124),
                ('some-type1', 125),
                ('some-type2', 245),
                ('some-type2', 246),
                ('some-type2', 247)
            }
        )

    def test_create_set_from_compressed_report(self):
        # Tests whether vulnerability sets for compressed reports match those from
        # their corresponding uncompressed ones.
        for report in os.listdir(fetch_file(resource_uri("reports/"))):
            uncompressed_report = load_json(fetch_file(resource_uri("reports/DAOBug.json")))
            expected_set = VulnerabilitiesSet.from_uncompressed_report(uncompressed_report)

            request_id = uncompressed_report['request_id']
            config = fetch_config(inject_contract=True)
            encoder = ReportEncoder(config)
            compressed_report = encoder.compress_report(uncompressed_report, request_id)
            decompressed_report = encoder.decode_report(compressed_report, request_id)
            found_set = VulnerabilitiesSet.from_uncompressed_report(decompressed_report)

            self.assertEquals(expected_set, found_set)
