class EthConfigHandler(BaseConfigHandler):

    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)

    BaseConfigHandler.raise_err(config.get("name") is not None, "Missing provider name")
    
    endpoint_uri = config.get("args", {}).get("metadata", "").replace(
        "${auth-token}",
        context.auth_token
    )

    return {{"args": {"endpoint_uri": endpoint_uri}}, **config}


class EthProviderFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(EthConfigHandler(component_name))

    def create_component(self, config, context=None):
        provider = config["name"]

        if provider == "HTTPProvider":
            args = get(config, '/args', accept_none=False)
            return HTTPProvider(**args)

        if provider == "IPCProvider":
            args = get(config, '/args', accept_none=False)
            return IPCProvider(**args)

        if provider == "EthereumTesterProvider":
            return EthereumTesterProvider()

        raise ConfigurationException("Unknown/Unsupported provider: {0}".format(provider))

