####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

import json
import os
import psutil
import sha3
import socket
import urllib

from log_streaming import get_logger


class MetricCollector:

    def __init__(self, config):
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__config = config
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
                self.__logger.debug("Metrics sent successfully to '{0}'".format(
                        self.__config.metric_collection_destination_endpoint
                    ),
                    metrics_json=metrics_json,
                    headers=req.headers,
                    response=response
                )
        except urllib.error.HTTPError as e:
            self.__logger.debug("HTTPError occurred when sending metrics",
                code=e.code,
                endpoint=self.__config.metric_collection_destination_endpoint
            )
        except urllib.error.URLError as e:
            self.__logger.debug("URLError occurred when sending metrics",
                reason=e.reason,
                endpoint=self.__config.metric_collection_destination_endpoint
            )
        except Exception as e:
            self.__logger.debug('Unhandled exception occurred when sending metrics',
                message=str(e),
                endpoint=self.__config.metric_collection_destination_endpoint
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

            if self.__config.metric_collection_destination_endpoint is not None:
                self.send_to_dashboard(metrics_json)

        except Exception as e:
            self.__logger.error("Could not collect metrics due to the error: \"" + str(e) + "\"")
