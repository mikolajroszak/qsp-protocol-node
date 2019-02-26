from component import BaseConfigHandler
from component import BaseComponentFactory

class PrivateKeyFactoryFactoryConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)


class PrivateKeyFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(PKFactoryConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a GasPriceCalculator component
        """
        # TODO
        return None