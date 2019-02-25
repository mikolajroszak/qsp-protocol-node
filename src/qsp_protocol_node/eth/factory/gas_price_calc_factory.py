class GasPriceCalculatorConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

class GasPriceCalculatorFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(GasPriceCalculatorConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates a GasPriceCalculator component
        """
        # TODO
        pass



