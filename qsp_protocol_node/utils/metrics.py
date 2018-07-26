import psutil
import boto3
import socket
import os


class MetricCollector:

    def __init__(self, config):
        self.__client = boto3.client('cloudwatch')
        self.__config = config
        self.__logger = config.logger
        self.__process_identifier = "{0}-{1}".format(socket.gethostname(), os.getpid())

    def collect(self):
        try:
            self.__logger.info("Metrics",
                               metrics=True,
                               processIdentifier=self.__process_identifier,
                               ethBlockNumber=self.__config.web3_client.eth.blockNumber,
                               ethNodeVersion=self.__config.web3_client.version.node,
                               ethProtocolVersion=self.__config.web3_client.version.ethereum,
                               hostCpu=psutil.cpu_percent(),
                               hostMemory=psutil.virtual_memory().percent,
                               hostDisk=psutil.disk_usage('/').percent,
                               minPrice=self.__config.min_price,
                               account=self.__config.account
                               )
        except Exception as e:
            self.__logger.error("Could not collect metrics due to the error: \"" + str(e) + "\"")
