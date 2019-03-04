####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from component import BaseConfigHandler
from component import BaseConfigHandler
from component import BaseConfigComponentFactory
from eth_infra import GasPriceCalculator
from utils.dictionary import get

class GasPriceCalculatorConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)

        strategy = get(config, '/strategy', accept_none=False)
        BaseConfigHandler.raise_err(
            strategy not in ['static', 'dynamic'], 
            "Unsupported strategy {0}".format(config['strategy'])
        )

        max_price_wei = get(config, '/max_price_wei', default=-1) 
        
        if strategy == 'static':
            default_gas_price_wei = get(config, '/default_gas_price_wei', accept_none=False)
            BaseConfigHandler.raise_err(
                max_price_wei > 0 and default_gas_price_wei > max_gas_price_wei
            )

        return config
            

class GasPriceCalculatorFactory(BaseConfigComponentFactory):
    def __init__(self, component_name):
        super().__init__(GasPriceCalculatorConfigHandler(component_name))

    def create_component(self, config, context):
        """
        Creates a GasPriceCalculator component
        """
        print("===> GasPriceCalculatorFactory. config is {0}".format(config))
        return GasPriceCalculator(context.web3_client, config)



