####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the configuration for executing a QSP Audit node,
as loaded from an input YAML file
"""
import importlib
import yaml


class Config:

    @classmethod
    def __load_yaml(cls, config_path):
        config_dictionary = None
        with open(config_path) as yaml_file:
            config_dictionary = yaml.load(yaml_file)
            
        return config_dictionary

    @classmethod
    def __get_init_order(cls, factories_dictionary):
        factories_list = [(name, factories_dictionary[name]['init_order']) for name in factories_dictionary]
        factories_list.sort(key=lambda name_order_pair: name_order_pair[1])
        return  [name for (name, _) in factories_list]


    def __init__(self, yaml_config_file, eth_passphrase, environment):
        self.__properties = {
            'config_file': yaml_config_file,
            'eth_passphrase': eth_passphrase,
            'eth_auth_token': eth_auth_token,
            'environment': environment,
            'node_version': '2.0.0'
        }

    def create_components(self):

        # Loads the config.yaml file as a dictionary
        config_dictionary = Config.__load_yaml(self.config_file, self.environment)
        config_dictionary = config_dictionary[self.environment]

        # Loads the factories setting as a dictionary
        factories_path = "{}/factories.yaml".format(
            os.path.dirname(os.path.realpath(__file__))
        )
        factories_dictionary = Config.__load_yaml(factories_path)
        
        # Makes all attributes (non-components) as properties of this object
        for attr in set(config_dictionary.keys()) - set(factories_dictionary.keys()):
            self.__properties[attr] = config_dictionary[attr]

        # Creates all components following the self-declared order attributes in
        # the factories.yaml file, registering each component as a property in this object
        for component_name in Config.__get_init_order(factories_dictionary):
            factory_def = factories_dictionary['component_name']['factory']

            factory_module = importlib.import_module(factory_def['module'])
            factory_class = getattr(factory_module, factory_def['class'])
            
            factory = factory_class(component_name)
            component_config = factory.config_handler.parse(config_dict.get(component_name), context=self)
            component = factory.create_component(component_config, context=self)
            
            # Sets the newly created component as a property in the config object
            self.__properties[component_name] = component

        ConfigValidator.check(self)

        def __getattr__(self, name):
            if name in self.__properties:
                return self.__properties[name]

            raise AttributeError(f"'{self.__class__.__qualname__}' object has no attribute '{name}'")
            
        def __setattr__(self, name,  value):
            if name in self.__properties:
                raise AttributeError("can't set attribute")

            super().__setattr__(name, value)
    