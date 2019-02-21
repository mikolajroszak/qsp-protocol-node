from utils.dictionary.path import get

class LogStreamerConfigHandler:
    
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


class LogStreamProviderFactory:

    __config_handler = LogStreamerConfigHandler()

    @property
    def config_handler(self):
        return __config_handler

    def create_component(config, context=None):
        is_enabled = config['is_enabled']
        if not is_enabled:
            return None

        provider_name = get('/name', accept_none=False)

        # Currently we only support a single provider
        if provider_name not in ["CloudWatchProvider"]:
            raise Exception(
                "Unknown/Unsupported streaming provider: {0}".format(provider_name))

        from streaming import CloudWatchProvider
        return CloudWatchProvider(context.account, config)
        


