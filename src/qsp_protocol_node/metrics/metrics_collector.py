####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

# TODO Move this class to its own module /qsp_protocol_node/metrics/collectory.py

import json
import os
import psutil
import sha3
import socket
import urllib

from component import BaseConfigComponent


class MetricsCollector(BaseConfigComponent):

    def __init__(self, config):
        super().__init__(config)
        self.__process_identifier = "{0}-{1}".format(socket.gethostname(), os.getpid())

    def __get_auth_header(self, content):
        k = sha3.keccak_256()
        k.update(content)
        message_hash = k.hexdigest()
        signed_message = self.__config.web3_client.eth.account.signHash(
            message_hash,
            private_key=self.__config.account_private_key
        )

        return "Digest: {0}".format(
            self.__config.web3_client.toHex(signed_message['signature'])
        )

    def send_to_dashboard(self, metrics_json):
        if not self.is_enabled:
            raise Exception(f"Cannot send metrics to dashboard: {self.component_name} is not enabled")

        data = json.dumps(metrics_json, separators=None).encode('utf-8')
        req = urllib.request.Request(
            url=self.__config.metric_collection_destination_endpoint,
            data=data,
            headers={
                'content-type': 'application/json',
                 # the default user agent is often blocked
                'user-agent': 'Mozilla/5.0',
                'authorization': self.__get_auth_header(data)
            },
            method='POST'
        )
        try:
            with urllib.request.urlopen(req) as responseObject:
                response = responseObject.read()
                self.get_logger().debug("Metrics sent successfully to '{0}'".format(
                        self.__config.metric_collection_destination_endpoint
                    ),
                    metrics_json=metrics_json,
                    headers=req.headers,
                    response=response
                )
        except urllib.error.HTTPError as e:
            self.get_logger().debug("HTTPError occurred when sending metrics",
                code=e.code,
                endpoint=self.__config.metric_collection_destination_endpoint
            )
        except urllib.error.URLError as e:
            self.get_logger().debug("URLError occurred when sending metrics",
                reason=e.reason,
                endpoint=self.__config.metric_collection_destination_endpoint
            )
        except Exception as e:
            self.get_logger().debug('Unhandled exception occurred when sending metrics',
                message=str(e),
                endpoint=self.__config.metric_collection_destination_endpoint
            )

    def collect_and_send(self):
        if not self.is_enabled:
            raise Exception(f"Cannot collect and send metrics: {self.component_name} is not enabled")

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

            self.get_logger().info("Metrics", metrics_json=metrics_json)
            if self.__config.metric_collection_destination_endpoint is not None:
                self.send_to_dashboard(metrics_json)

        except Exception as e:
            self.get_logger().error("Could not collect metrics due to the error: \"" + str(e) + "\"")

