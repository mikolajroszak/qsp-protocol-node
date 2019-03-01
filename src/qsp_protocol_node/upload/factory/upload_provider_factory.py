####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from component import BaseConfigHandler
from component import BaseConfigComponentFactory
from component import ConfigurationException

class UploadProviderConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)
        
    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)

        if config == None:
            return {'name': "",  'is_enabled': False, 'args': {}}

        # Forces users to specify `is_enabled`: False in their config.yaml
        return dict({'is_enabled': True}, **config)

class UploadProviderFactory(BaseConfigComponentFactory):
    
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
            return None

        # Provider is enabled and should therefore have a name
        name = config['name']
        if name == "S3Provider":
            return S3Provider(context.account, config)

        raise ConfigurationException(
            "Unknown/Unsupported provider: {0}".format(upload_provider_name))