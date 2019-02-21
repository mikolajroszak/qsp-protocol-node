class BaseConfigHandler:
    def __init__(self, component_name):
        self.__component_name = component_name

    @property
    def component_name(self):
        return self.__component_name

    def parse(self. config, context=None):
        return config


class BaseComponentFactory:
    def __init__(self, config_handler)
        self.__config_handler = config_handler

    @property
    def config_handler(self):
        return self.__config_handler

    def create_component(self, config, context=None)
        raise Exception("Unimplemented method create_component")
