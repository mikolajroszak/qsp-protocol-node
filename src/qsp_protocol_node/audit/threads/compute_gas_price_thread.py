####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread updating the min price for the QSP Audit node implementation.
"""

from threading import Thread

from .qsp_thread import QSPThread
from utils.eth import get_gas_price


class ComputeGasPriceThread(QSPThread):

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        QSPThread.__init__(self, config)

    def start(self):
        """
        Updates min price every 24 hours.
        """
        gas_price_thread = Thread(target=self.__execute, name="compute gas price thread")
        gas_price_thread.start()
        return gas_price_thread

    def __execute(self):
        """
        Defines the function to be executed and how often.
        """
        self.run_block_mined_thread("compute_gas_price", self.compute_gas_price)

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
        self.logger.debug("Current gas price: {0}".format(str(gas_price)))
