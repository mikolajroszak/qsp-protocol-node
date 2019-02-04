####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Exceptions thrown by the audit node that may require
special handling.
"""


class ExecutionException(Exception):
    pass


class NotEnoughStake(Exception):
    pass


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
