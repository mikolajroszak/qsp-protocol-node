####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from enum import Enum
from node_logging import get_logger

class ConfigType(Enum):
    INTERNAL = 'internal'
    OPTIONAL = 'optional'
    MANDATORY = 'mandatory'

class ConfigurationException(Exception):
    """
    A specialized exception for signaling configuration errors.
    """

class BaseConfigHandler(object):
    def __init__(self, component_name):
        self.__component_name = component_name

    def get_logger(self):
        return get_logger(self.__class__.__qualname__)

    @property
    def component_name(self):
        return self.__component_name

    def parse(self, config, config_type, context=None):
        if config_type is ConfigType.INTERNAL and config is not None:
            raise ConfigurationException(f"Internal components cannot be configured externally")

        if config_type is ConfigType.MANDATORY and config is None:
            raise ConfigurationException(f"Could not find '{self.component_name}' in configuration'")

        # Else, it an optional component (may or not have an associated config)
        return config

    @classmethod
    def raise_err(cls, cond=True, msg=""):
        """
        Raises an exception if the given condition holds.
        """
        if cond:
            raise ConfigurationException("Cannot initialize QSP node. {0}".format(msg))


class BaseConfigComponentFactory:
    def __init__(self, config_handler):
        self.__config_handler = config_handler

    def get_logger(self):
        return get_logger(self.__class__.__qualname__)

    @property
    def config_handler(self):
        return self.__config_handler

    def create_component(self, config, context=None):
        raise Exception("Unimplemented method create_component")

class BaseConfigComponent(dict):

    def __init__(self, config={}):
        super().__init__()
        for key in config:
            dict.__setitem__(self, key, config[key])

    def get_logger(self):
        return get_logger(self.__class__.__qualname__)

    def __getattr__(self, attr):
        try:
            return dict.__getitem__(self, attr)
        except KeyError:
            raise AttributeError(attr)

       
