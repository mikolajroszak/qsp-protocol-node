import watchtower

from boto3.session import Session
from pythonjsonlogger.jsonlogger import JsonFormatter


class CloudWatchProvider:

    def __init__(self, account, log_group, log_stream, send_interval_seconds):
        self.__stream_name = log_stream.replace('{id}', account)
        self.__log_group = log_group
        self.__send_interval = send_interval_seconds

    def get_handler(self):
        handler = watchtower.CloudWatchLogHandler(
            log_group=self.__log_group,
            stream_name=self.__stream_name,
            send_interval=self.__send_interval,
            boto3_session=Session(),
            create_log_group=False,
        )

        handler.setFormatter(JsonFormatter('%(message)s %(threadName)s %(lineno)d %(pathname)s'))
        return handler
