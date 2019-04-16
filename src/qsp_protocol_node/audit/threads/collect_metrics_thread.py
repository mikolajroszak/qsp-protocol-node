####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread for collecting metrics for the QSP Audit node implementation.
"""
from utils.metrics import MetricCollector

from .qsp_thread import TimeIntervalPollingThread


class CollectMetricsThread(TimeIntervalPollingThread):

    def collect_and_send(self):
        """
        Collects current metrics for the node and sends logs.
        """
        self.__metric_collector.collect_and_send()

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        TimeIntervalPollingThread.__init__(
            self,
            config,
            target_function=self.collect_and_send,
            polling_interval=config.metric_collection_interval_seconds,
            thread_name="collect metrics thread",
            start_with_call=False
        )
        self.__metric_collector = MetricCollector(config)
