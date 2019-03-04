####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from component import BaseConfigHandler
from component import BaseConfigComponentFactory
from component import ConfigurationException

from time import sleep
from web3 import Web3

class Web3ClientConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)


class Web3ClientFactory(BaseConfigComponentFactory):
    def __init__(self, component_name):
        super().__init__(Web3ClientConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a Web3Client component
        """
        MAX_ATTEMPTS = 30
        attempts = 0

        # Default retry policy is as follows:
        # 1) Makes a query (in this case, "eth.accounts")
        # 2) If connected, nothing else to do
        # 3) Otherwise, keep trying at most max_attempts, waiting 10s per each iteration
        web3_client = Web3(context.eth_provider)
        connected = False

        while attempts < MAX_ATTEMPTS and not connected:
            try:
                web3_client = Web3(context.eth_provider)

                # Tries to probe ethereum client is not reachable
                _ = web3_client.eth.accounts

                connected = True
                self.get_logger().debug("Connected on attempt {0}".format(attempts))
            except Exception as exception:
                # An exception has occurred. Increment the number of attempts
                # made, and retry after 5 seconds
                attempts = attempts + 1
                self.get_logger().debug(
                    "Connection attempt ({0}) failed due to {1}. Retrying in 10 seconds".format(attempts, str(exception)))
                sleep(10)

        if not connected:
            raise ConfigurationException(
                "Could not connect to ethereum node (time out after {0} attempts).".format(
                    MAX_ATTEMPTS
                )
            )
        return web3_client