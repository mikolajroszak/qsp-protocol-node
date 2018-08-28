####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Tests that JSON reports adhere to the analyzer_integration schema
"""
import os
import unittest
import json
from jsonschema import (
    validate,
    SchemaError,
    ValidationError
)

from utils.io import fetch_file, load_json
from helpers.resource import (
    resource_uri,
    project_root,
)


class TestJsonReportValidation(unittest.TestCase):
    schema = None

    @classmethod
    def setUpClass(cls):
        file_path = os.path.realpath(__file__)
        schema_file = '{0}/../../analyzers/schema/analyzer_integration.json'.format(
            os.path.dirname(file_path))
        with open(schema_file) as schema_data:
            cls.schema = json.load(schema_data)

    def validate_report(self, report_path):
        report = load_json(fetch_file(resource_uri(report_path)))
        validate(report, self.schema)

    def test_DAOBug(self):
        self.validate_report("reports/DAOBug.json")

    def test_BasicToken(self):
        self.validate_report("reports/BasicToken.json")

    def test_DappBinWallet(self):
        self.validate_report("reports/DappBinWallet.json")

    def test_DaoBugWithBadProperty(self):
        # this test should fail as the report has correctly named the "analyzers_reports" property
        try:
            self.validate_report("reports/DAOBugWithBadProperty.json")
            self.fail("This report is incorrect and an exception should be raised.")
        except ValidationError:
            pass


if __name__ == '__main__':
    unittest.main()
