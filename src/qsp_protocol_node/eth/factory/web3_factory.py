class Web3ConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, context=None):
        # TODO
        pass


class Web3ClientFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(Web3ConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a GasPriceCalculator component
        """
        #TODO
        pass