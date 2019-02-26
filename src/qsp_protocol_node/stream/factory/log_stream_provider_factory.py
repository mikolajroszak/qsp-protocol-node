from component import BaseConfigHandler
from component import BaseComponentFactory


# TODO: refactor this to avoid dup with upload_provider_factory.py
class LogStreamerConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)
 
        if config is None:
            return {'name': "",  'is_enabled': False, 'args': {}}

        # Forces users to specify `is_enabled`: False in their config.yaml
        return {'is_enabled': True, **config}


class LogStreamProviderFactory(BaseComponentFactory):

    def __init__(self, component_name):
        super().__init__(LogStreamerConfigHandler(component_name))

    def create_component(self, config, context=None):
        is_enabled = config['is_enabled']
        if not is_enabled:
            return None

        provider_name = config['name']

        # Currently we only support a single provider
        if provider_name not in ["CloudWatchProvider"]:
            raise Exception(
                "Unknown/Unsupported streaming provider: {0}".format(provider_name))

        from stream import CloudWatchProvider
        return CloudWatchProvider(context.account, config)
        


