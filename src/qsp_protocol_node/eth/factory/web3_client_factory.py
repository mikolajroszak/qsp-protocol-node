from component import BaseConfigHandler
from component import BaseComponentFactory

class Web3ClientConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, context=None):
        # TODO
        return None


class Web3ClientFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(Web3ClientConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a GasPriceCalculator component
        """
        #TODO
        return None