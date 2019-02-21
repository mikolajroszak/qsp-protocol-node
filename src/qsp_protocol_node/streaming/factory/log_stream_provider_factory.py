from utils.dictionary.path import get

# TODO: refactor this to avoid dup with upload_provider_factory.py
class LogStreamerConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, context=None):
        if config == None:
            return {'name': "",  'is_enabled': False, 'args': {}}

        # Forces users to specify `is_enabled`: False in their config.yaml
        return {'is_enabled': True, **config}


class LogStreamProviderFactory:

    def __init__(self, component_name):
        super().__init__(LogStreamerConfigHandler(component_name))

    def create_component(self, config, context=None):
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
        


