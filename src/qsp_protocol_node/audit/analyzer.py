####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Provides an interface for invoking the analyzer software.
"""

import json

from log_streaming import get_logger


class Analyzer:

    def __init__(self, wrapper):
        """
        Builds an Analyzer object from a given arguments string.
        """
        self.__wrapper = wrapper
        self.__logger = get_logger(self.__class__.__qualname__)

    def __repr__(self):
        """
        Represents the analyzer using the name of the wrapped analyzer
        """
        return "empty_analyzer_object" if self.__wrapper is None else self.__wrapper.analyzer_name

    @property
    def wrapper(self):
        return self.__wrapper

    def get_metadata(self, contract_path, request_id, original_file_name):
        """
        Returns the metadata {name, version, vulnerabilities_checked, command}
        associated with a call to the analyzer.
        """
        self.__logger.debug("Getting {0}'s metadata. About to check {1}".format(
            self.wrapper.analyzer_name,
            contract_path,
        ),
            requestId=request_id,
        )
        return self.wrapper.get_metadata(contract_path, request_id, original_file_name)

    def check(self, contract_path, request_id, original_file_name):
        """
        Checks for potential vulnerabilities in a target contract writen in a given
        version of Solidity, writing the result in a json report.
        """
        self.__logger.debug("Running {0}'s wrapper. About to check {1}".format(
            self.wrapper.analyzer_name,
            contract_path,
        ),
            requestId=request_id,
        )

        json_report = self.__wrapper.check(contract_path, request_id, original_file_name)
        str_report = json.dumps(json_report)
        self.__logger.debug("{0}'s wrapper finished execution. Produced report is {1}".format(
            self.wrapper.analyzer_name,
            str_report,
        ),
            requestId=request_id,
        )

        return json_report
