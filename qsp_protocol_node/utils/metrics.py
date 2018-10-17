####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import psutil
import socket
import os
import json
import urllib

class MetricCollector:

    def __init__(self, config):
        self.__config = config
        self.__logger = config.logger
        self.__process_identifier = "{0}-{1}".format(socket.gethostname(), os.getpid())

    def send_to_dashboard(self, metrics_json):
        data = json.dumps(metrics_json).encode('utf8')
        req = urllib.request.Request(
            url = self.__config.metric_collection_destination_endpoint,
            data = data,
            headers = {
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0' # the default user agent is often blocked
            },
            method = 'POST'
        )
        try:
            with urllib.request.urlopen(req) as responseObject:
                response = responseObject.read()
                self.__logger.debug("Metrics sent successfully to '{0}'".format(
                        self.__config.metric_collection_destination_endpoint
                    ),
                    metrics_json = metrics_json,
                    response = response
                )
        except urllib.error.HTTPError as e:
            self.__logger.debug("HTTPError occurred when sending metrics",
                code = e.code,
                endpoint = self.__config.metric_collection_destination_endpoint
            )
        except urllib.error.URLError as e:
            self.__logger.debug("URLError occurred when sending metrics",
                reason = e.reason,
                endpoint = self.__config.metric_collection_destination_endpoint
            )
        except Exception as e:
            self.__logger.debug('Unhandled exception occurred when sending metrics',
                message = str(e),
                endpoint = self.__config.metric_collection_destination_endpoint
            )

    def collect_and_send(self):
        try:
            metrics_json = {
                'processIdentifier': self.__process_identifier,
                'ethBlockNumber': self.__config.web3_client.eth.blockNumber,
                'ethNodeVersion': self.__config.web3_client.version.node,
                'ethProtocolVersion': self.__config.web3_client.version.ethereum,
                'contractVersion': self.__config.contract_version,
                'nodeVersion': self.__config.node_version,
                'hostCpu': psutil.cpu_percent(),
                'hostMemory': psutil.virtual_memory().percent,
                'hostDisk': psutil.disk_usage('/').percent,
                'minPrice': self.__config.min_price_in_qsp,
                'account': self.__config.account
            }

            self.__logger.info("Metrics", metrics_json = metrics_json)
            if self.__config.metric_collection_destination_endpoint is not None:
                self.send_to_dashboard(metrics_json)

        except Exception as e:
            self.__logger.error("Could not collect metrics due to the error: \"" + str(e) + "\"")
