"""
Provides an interface for invoking the analyzer software.
"""

import json

from utils.io import digest


class AnalyzerRunException(Exception):
    def __init__(self, message, output):
        self.__message = message
        self.__output = output

    @property
    def message(self):
        return self.__message

    @property
    def output(self):
        return self.__output


class Analyzer:

    def __init__(self, wrapper, logger):
        """
        Builds an Analyzer object from a given arguments string.
        """
        self.__wrapper = wrapper
        self.__logger = logger

    @property
    def wrapper(self):
        return self.__wrapper

    def check(self, contract_path, request_id):
        """
        Checks for potential vulnerabilities in a target contract writen in a given
        version of Solidity, writing the result in a json report.
        """
        self.__logger.debug("Running {0}'s wrapper. About to check {1}".format(
                self.__wrapper.analyzer_name, contract_path
            ),
            requestId=request_id,
        )

        json_report = self.__wrapper.check(contract_path, request_id)
        str_report = json.dumps(json_report)
        json_report['hash'] = digest(str_report)

        self.__logger.debug("{0}'s wrapper finished execution. Produced report is {1}".format(
                self.__wrapper.analyzer_name,
                str_report,
            ),
            requestId=request_id,
        )

        return json_report
