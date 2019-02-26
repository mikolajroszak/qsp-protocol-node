####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import watchtower

from utils.dictionary.path import get

from boto3.session import Session
from pythonjsonlogger.jsonlogger import JsonFormatter

# TODO Rename this to LogStreamingProvider
class CloudWatchProvider:

    def __init__(self, account, config):
        print("===> CloudWatchProvider config " + str(config))
        self.__stream_name = get(
            config, '/args/log_stream', accept_none=False
        ).replace('{id}', account)

        self.__log_group = get(config, '/args/log_group', accept_none=False)
        self.__send_interval_seconds = get(config, '/args/send_interval_seconds', 
            accept_none=False
        )

    def get_handler(self):
        handler = watchtower.CloudWatchLogHandler(
            log_group=self.__log_group,
            stream_name=self.__stream_name,
            send_interval=self.__send_interval_seconds,
            boto3_session=Session(),
            create_log_group=False,
        )

        handler.setFormatter(JsonFormatter('%(message)s %(threadName)s %(lineno)d %(pathname)s'))
        return handler
