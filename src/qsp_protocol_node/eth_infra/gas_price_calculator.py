####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from component import BaseConfigComponent

class GasPriceCalculator(BaseConfigComponent):
    def __init__(self, web3_client, config):
        super().__init__(config)
        self.__web3_client = web3_client
    
    def __get_dynamic_price(self):
        try:
            SingletonLock.instance().lock.acquire()
            return self.__web3_client.eth.gasPrice
        finally:
            try:
                SingletonLock.instance().lock.release()
            except Exception as error:
                self.get_logger().debug(
                    "Error when releasing a lock in gas price read {0}".format(str(error))
                )

    def get(self):
        """
        Queries recent blocks to set a baseline gas price, or uses a default static gas price
        """
        gas_price = None
        # If we're not using the dynamic gas price strategy, just return the default
        if self.strategy == "static":
            gas_price = self.default_price_wei
        else:
            gas_price = self.__get_dynamic_price()

        return int(min(gas_price, self.max_price_wei))
