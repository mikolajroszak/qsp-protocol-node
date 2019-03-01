####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import ntpath
import unittest
import structlog
import logging
import logging.config
from eth.tools.logging import (
    setup_trace_logging
)
from helpers.resource import resource_uri
from pprint import pprint
from deepdiff import DeepDiff
from utils.io import fetch_file, load_json


class QSPTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging()

    def compare_json(self, audit_file, report_file_path, json_loaded=False, ignore_id=False):
        if not json_loaded:
            actual_json = load_json(audit_file)
        else:
            actual_json = audit_file
        expected_json = load_json(fetch_file(resource_uri(report_file_path)))
        if ignore_id:
            expected_json['request_id'] = actual_json['request_id']

        diff = DeepDiff(
            actual_json,
            expected_json,
            exclude_paths={
                "root['contract_uri']",
                # There is no keystore used for testing. Accounts
                # are dynamic and therefore cannot be compared
                "root['auditor']",
                "root['requestor']",
                # Path is different depending on whether running inside Docker
                "root['timestamp']",
                "root['start_time']",
                "root['end_time']",
                "root['analyzers_reports'][0]['analyzer']['command']",
                "root['analyzers_reports'][0]['coverages'][0]['file']",
                "root['analyzers_reports'][0]['potential_vulnerabilities'][0]['file']",
                "root['analyzers_reports'][0]['start_time']",
                "root['analyzers_reports'][0]['end_time']",
                "root['analyzers_reports'][1]['analyzer']['command']",
                "root['analyzers_reports'][1]['coverages'][0]['file']",
                "root['analyzers_reports'][1]['potential_vulnerabilities'][0]['file']",
                "root['analyzers_reports'][1]['start_time']",
                "root['analyzers_reports'][1]['end_time']",
                "root['analyzers_reports'][2]['analyzer']['command']",
                "root['analyzers_reports'][2]['coverages'][0]['file']",
                "root['analyzers_reports'][2]['potential_vulnerabilities'][0]['file']",
                "root['analyzers_reports'][2]['start_time']",
                "root['analyzers_reports'][2]['end_time']",
            }
        )
        pprint(diff)
        self.assertEqual(diff, {})
        self.assertEqual(ntpath.basename(actual_json['contract_uri']),
                         ntpath.basename(expected_json['contract_uri']))


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s[%(threadName)s] %(message)s',
    )

    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)

    structlog.configure_once(
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs]
    )
    level_map = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10,
        'TRACE': 5,
        'NOTSET': 0,
    }
    dict_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                'format': '%(message)s %(threadName)s %(lineno)d %(pathname)s ',
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
            }
        },
        'handlers': {
            'json': {
                'class': 'logging.StreamHandler',
                'formatter': 'json'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'json',
                'filename': '/var/log/qsp-protocol/qsp-protocol.log',
                'mode': 'a',
                'maxBytes': 10485760,
                'backupCount': 5
            }
        },
        'loggers': {
            '': {
                'handlers': ['json', 'file'],
                'level': level_map["DEBUG"],
            }
        }
    }
    logging.config.dictConfig(dict_config)
    setup_trace_logging()
