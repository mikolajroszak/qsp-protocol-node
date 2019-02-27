from component import BaseConfigHandler
from component import BaseComponentFactory
from component import ConfigurationException

from web3 import HTTPProvider
from web3 import IPCProvider
####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from web3 import EthereumTesterProvider

class EthConfigHandler(BaseConfigHandler):

    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)

        BaseConfigHandler.raise_err(config.get("name") is None, "Missing provider name")
        
        endpoint_uri = config.get("args", {}).get("metadata", "").replace(
            "${auth_token}",
            context.config_vars.get('auth_token', '')
        )

        return dict({"args": {"endpoint_uri": endpoint_uri}}, **config)


class EthProviderFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(EthConfigHandler(component_name))

    def create_component(self, config, context=None):
        provider = config["name"]

        if provider == "HTTPProvider":
            return HTTPProvider(**config['args'])

        if provider == "IPCProvider":
            return IPCProvider(**config['args'])

        if provider == "EthereumTesterProvider":
            if context.keystore is not None:
                raise ConfigurationException("EthereumTesterProvider does not use a keystore")
                
            return EthereumTesterProvider()

        raise ConfigurationException("Unknown/Unsupported provider: {0}".format(provider))

