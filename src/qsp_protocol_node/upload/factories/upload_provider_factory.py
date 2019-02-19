from utils.dictionary.path import get

class UploadProviderConfigHandler:

    def default_config(self):
        return {
            'name': "", 
            'is_enabled': False, 
            'args': {}
        }

    def parse(self, config):
        if config == None:
            return default_config

        return config

class UploadProviderFactory(ComponentFactory):
    
    __config_handler = UploadProviderConfigHandler()

    @property
    def config_handler(self):
        return __config_handler
    
    def create_component(upload_provider_config, context=None):
        """
        Creates a report upload provider.
        """
        # Supported providers:
        #
        # S3Provider

        is_enabled = get(upload_provider_config,
            '/is_enabled', False)

        if not is_enabled:
            return DummyProvider()

        # Provider is enabled and should therefore have a name
        name = get(upload_provider_config,
            '/name', accept_none=False)

        if upload_provider_name == "S3Provider":
            if account is None:
                raise ConfigurationException("Missing account for upload provider")
            return S3Provider(account, **upload_provider_args)

        raise ConfigurationException(
            "Unknown/Unsupported provider: {0}".format(upload_provider_name))