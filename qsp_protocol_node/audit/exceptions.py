"""
Exceptions thrown by the audit node that may require
special handling.
"""


class ExecutionException(Exception):
    pass


class NonWhitelistedNodeException(ExecutionException):
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
