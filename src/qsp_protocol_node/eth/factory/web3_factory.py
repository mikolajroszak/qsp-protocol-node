class Web3(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, context=None):
        if config is not None:


class GasPriceCalculatorFactory(BaseConfigFactory):
    def __init__(self, component_name):
        super().__init__(GasPriceCalculatorConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a GasPriceCalculator component
        """