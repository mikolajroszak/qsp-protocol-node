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
from threading import Thread

from .qsp_thread import QSPThread


class CollectMetricsThread(QSPThread):

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        QSPThread.__init__(self, config)
        self.__metric_collector = MetricCollector(config)

    def start(self):
        """
        Updates min price every 24 hours.
        """
        collect_metrics_thread = Thread(target=self.__execute, name="collect metrics thread")
        collect_metrics_thread.start()
        return collect_metrics_thread

    def __execute(self):
        """
        Defines the function to be executed and how often.
        """
        self.run_with_interval(self.__metric_collector.collect_and_send,
                               self.config.metric_collection_interval_seconds,
                               start_with_call=False)

    def collect_and_send(self):
        """
        Collects current metrics for the node and sends logs.
        """
        self.__metric_collector.collect_and_send()
