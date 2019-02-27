####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from enum import Enum

class ConfigType(Enum):
    INTERNAL = 'internal'
    OPTIONAL = 'optional'
    MANDATORY = 'mandatory'

class ConfigurationException(Exception):
    """
    A specialized exception for signaling configuration errors.
    """

class BaseConfigHandler:
    def __init__(self, component_name):
        self.__component_name = component_name

    @property
    def component_name(self):
        return self.__component_name

    def parse(self, config, config_type, context=None):
        if config_type is ConfigType.INTERNAL and config is not None:
            raise ConfigurationException(f"Internal components cannot be configured externally")

        if config_type is ConfigType.MANDATORY and config is None:
            raise ConfigurationException(f"Could not find '{self.component_name}' in configuration'")

        return config

    @classmethod
    def raise_err(cls, cond=True, msg=""):
        """
        Raises an exception if the given condition holds.
        """
        if cond:
            raise ConfigurationException("Cannot initialize QSP node. {0}".format(msg))


class BaseComponentFactory:
    def __init__(self, config_handler):
        self.__config_handler = config_handler

    @property
    def config_handler(self):
        return self.__config_handler

    def create_component(self, config, context=None):
        raise Exception("Unimplemented method create_component")
