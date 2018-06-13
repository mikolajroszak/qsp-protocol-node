import watchtower

from boto3.session import Session
from utils.node_key import NodeKey


class CloudWatchProvider:
    def __init__(self, log_group, log_stream, send_interval_seconds):
        boto3_session = Session()
        self.__dictConfig = {
            'class': 'watchtower.CloudWatchLogHandler',
            'boto3_session': boto3_session,
            'log_group': log_group,
            'stream_name': log_stream.replace('{id}', NodeKey.fetch()),
            'formatter': 'json',
            'send_interval': send_interval_seconds
        }

    def get_handler(self):
        return watchtower.CloudWatchLogHandler()

    def get_dict_config(self):
        return self.__dictConfig
