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
from eth_infra import EthWrapper

class EthWrapperFactory(BaseConfigComponentFactory):
    def __init__(self, component_name):
        super().__init__(BaseConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates an EthWrapper component
        """
        return EthWrapper(
            context.account,
            context.gas_price_calculator,
            context.web3_client,
            context.block_mined_polling_sec,
            context.transaction_confirmation_n_blocks
        )
        