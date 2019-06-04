####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
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

    def __close_evt_manager(self, config):
        """
        Closes the event manager. This has to be done before asserting the final database state.
        """
        config.event_pool_manager.close()

    @staticmethod
    def __find_difference(list1, list2):
        """
        Returns the difference between two lists of audit_evt records.
        """
        for x in [item for item in list1 if item not in list2]:
            for y in [y for y in list2 if y['request_id'] == x["request_id"]]:
                for key in x.keys():
                    if x[key] != y[key]:
                        msg = "Key: {}, Value 1:{} Values 2:{} \nList1: {}\nList2: {}"
                        return msg.format(key, x[key], y[key], list1, list2)
        return "No difference found"

    def assert_event_table_contains(self, config, data, ignore_keys=(), close=True):
        """Checks that the table audit_evt contains all dictionaries that are in data"""

        query = "select * from audit_evt"
        content = config.event_pool_manager.sql3lite_worker.execute(
            query)
        if close:
            self.__close_evt_manager(config)
        self.assertEqual(len(content), len(data), "{} is not {}".format(content, data))
        for key in ignore_keys:
            for row in content:
                row[key] = "Ignored"
            for row in data:
                row[key] = "Ignored"
        self.assertEqual(len([row for row in content if row in data]), len(data),
                         QSPTest.__find_difference(data, content))

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
                "root['version']",
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
                # Once scripts are either executed or skipped. The traces at position 1 differ.
                "root['analyzers_reports'][0]['trace'][1]",
                "root['analyzers_reports'][1]['trace'][1]",
                "root['analyzers_reports'][2]['trace'][1]"
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
