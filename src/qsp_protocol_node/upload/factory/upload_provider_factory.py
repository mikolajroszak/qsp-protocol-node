from utils.dictionary.path import get

class UploadProviderConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)
        
    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)

        if config == None:
            return {'name': "",  'is_enabled': False, 'args': {}}

        # Forces users to specify `is_enabled`: False in their config.yaml
        return {'is_enabled': True, **config}

class UploadProviderFactory(BaseComponentFactory):
    
    def __init__(self, component_name):
        super().__init__(UploadProviderConfigHandler(component_name))
    
    def create_component(self, config, context=None):
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