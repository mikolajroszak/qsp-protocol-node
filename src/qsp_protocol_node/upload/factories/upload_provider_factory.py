from utils.dictionary.path import get

class UploadProviderConfigHandler:

    __default_config = {
        'is_enabled': False,
        'args': {}
    }

    @property
    def default_config(self):
        return self.__default_config

    def parse(self, config, context=None):
        if config == None:
            return self.__default_config

        return {**self.__default_config, **config}

class UploadProviderFactory:
    
    __config_handler = UploadProviderConfigHandler()

    @property
    def config_handler(self):
        return __config_handler
    
    def create_component(config, context=None):
        """
        Creates a report upload provider.
        """
        # Supported providers:
        #
        # S3Provider

        is_enabled = config['is_enabled']
        if not is_enabled:
            return DummyProvider(config)

        # Provider is enabled and should therefore have a name
        name = get(config, '/name', accept_none=False)
        if name == "S3Provider":
            return S3Provider(context.account, config)

        raise ConfigurationException(
            "Unknown/Unsupported provider: {0}".format(upload_provider_name))