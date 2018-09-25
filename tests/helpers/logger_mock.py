####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import apsw


class LoggerMock:

    def __init__(self):
        self.logged_error = False
        self.logged_warning = False
        self.err = None

    def output(self, msg, query, values, err):
        print(msg)
        print(query)
        print(values)
        print(err)
        if isinstance(err, apsw.BusyError):
            print("NOTE: If the error appears to be 'BusyError', your test failed mid-execution. "
                  "You might need to delete the test database file defined in test_config.yaml "
                  "(currently set to /tmp/evts.test) in order to resume test execution.")

    def error(self, msg, query, values, err):
        self.err = err
        self.logged_error = True
        self.output(msg, query, values, err)

    def warning(self, msg, query, values, err):
        self.err = err
        self.logged_warning = True
        self.output(msg, query, values, err)
