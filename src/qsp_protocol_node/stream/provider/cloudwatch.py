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
from stream import LogStreamProvider

from boto3.session import Session
from pythonjsonlogger.jsonlogger import JsonFormatter

class CloudWatchProvider(LogStreamProvider):

    def __init__(self, account, config):
        super().__init__(config)

        # Makes sure stream name is set and parameter is
        # pre-processed
        stream_name = get(
            config, '/args/stream_name', accept_none=False
        ).replace("${id}", account)
        config['args']['stream_name'] = stream_name

        # Makes sure group is set
        get(config, '/args/group', accept_none=False)

        # Makes sure send_interval_seconds is set
        get(config, '/args/send_interval_seconds', accept_none=False)

    @property
    def group(self):
        return self.args['group']

    @property
    def stream_name(self):
        return self.args['stream_name']

    @property
    def send_interval_seconds(self):
        return self.args['send_interval_seconds']

    @property
    def is_enabled(self):
        return self.config['is_enabled']

    def get_handler(self):
        handler = watchtower.CloudWatchLogHandler(
            log_group=self.log_group,
            stream_name=self.stream_name,
            send_interval=self.send_interval_seconds,
            boto3_session=Session(),
            create_log_group=False,
        )

        handler.setFormatter(JsonFormatter('%(message)s %(threadName)s %(lineno)d %(pathname)s'))
        return handler
