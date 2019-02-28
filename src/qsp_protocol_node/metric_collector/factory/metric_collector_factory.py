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
from component import BaseComponentFactory

class MetricCollectorConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, config_type, context=None):
        # TODO
        super().parse(config, config_type, context)
        return None

class MetricCollectorComponentFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(MetricCollectorConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a GasPriceCalculator component
        """
        # TODO
        pass



