class EthConfigHandler(BaseConfigHandler):

    def __init__(self, component_name):
        super().__init__(component_name)


class EthProviderFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(EthConfigHandler(component_name))

    def create_component(self, config, context=None):
        provider = get(config, '/name', accept_none=False)

        if provider == "HTTPProvider":
            args = get(config, '/args', accept_none=False)
            return HTTPProvider(**args)

        if provider == "IPCProvider":
            args = get(config, '/args', accept_none=False)
            return IPCProvider(**args)

        if provider == "EthereumTesterProvider":
            return EthereumTesterProvider()

        raise ConfigurationException("Unknown/Unsupported provider: {0}".format(provider))

