####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

"""
Provides the thread for computing gas price for the QSP Audit node implementation.
"""

from .qsp_thread import BlockMinedSubscriberThread
from utils.eth import get_gas_price


class ComputeGasPriceThread(BlockMinedSubscriberThread):

    def __on_block_mined(self, block_number):
        self.compute_gas_price()
        self.logger.debug("New block detected: {0}. Current gas price: {1}".format(
            str(block_number), str(self.config.gas_price_wei)))

    def compute_gas_price(self):
        """
        Queries recent blocks to set a baseline gas price, or uses a default static gas price
        """
        gas_price = None
        # if we're not using the dynamic gas price strategy, just return the default
        if self.config.gas_price_strategy == "static":
            gas_price = self.config.default_gas_price_wei
        else:
            gas_price = get_gas_price(self.config)
        gas_price = int(min(gas_price, self.config.max_gas_price_wei))
        # set the gas_price in config
        self.config.gas_price_wei = gas_price

    def __init__(self, config, block_mined_polling_thread):
        """
        Builds the thread object from the given input parameters.
        """
        BlockMinedSubscriberThread.__init__(
            self, config,
            target_function=self.__on_block_mined,
            thread_name="compute_gas_price thread",
            block_mined_polling_thread=block_mined_polling_thread
        )
        self.compute_gas_price()
