import os

from audit import Analyzer
from audit import Wrapper
from utils.io import dir_exists
from component import BaseConfigHandler
from component import BaseComponentFactory

from collections import OrderedDict
from pathlib import Path

class AnalyzersConfigHandler(BaseConfigHandler):

    def __init__(self, component_name):
        super().__init__(component_name)

    @classmethod
    def wrapper_dir(cls, analyzer_name):
        this_script_path = os.path.realpath(__file__)
        return "{0}/../../../../plugins/analyzers/wrappers/{1}".format(
            os.path.dirname(this_script_path),
            analyzer_name
        )

    def parse(self, config, config_type, context=None):
        parsed_config = OrderedDict()

        AnalyzersConfigHandler.raise_err(
            config is None or len(config) == 0, 
            "There has to be at least one configured analyzer to use"
        )

        for i, analyzer_config_dict in enumerate(config):
            # Each analyzer config is a dictionary of a single entry
            # <analyzer_name> -> {
            #     analyzer dictionary configuration
            # }

            # Gets ths single key in the dictionary (the name of the analyzer)
            analyzer_name = list(analyzer_config_dict.keys())[0]
            analyzer_config = config[i][analyzer_name]
            
            wrapper_home = AnalyzersConfigHandler.wrapper_dir(analyzer_name)
            AnalyzersConfigHandler.raise_err(
                not dir_exists(wrapper_home),
                "Cannot find wrapper in {0}".format(wrapper_home)
            )

            DEFAULT_STORAGE_DIR = "{0}/.{1}".format(
                str(Path.home()),
                analyzer_name,
            )
            storage_dir = os.path.realpath(analyzer_config.get('storage_dir', DEFAULT_STORAGE_DIR))
            
            DEFAULT_TIMEOUT_SEC = 60
            timeout_sec = analyzer_config.get('timeout_sec', DEFAULT_TIMEOUT_SEC)
            AnalyzersConfigHandler.raise_err(timeout_sec < 0, "timeout_sec must be a non-negative number")

            parsed_config[analyzer_name] = {
                'wrapper_home': wrapper_home,
                'storage_dir': storage_dir,
                'args': analyzer_config_dict.get('args', ''),
                'timeout_sec': timeout_sec,
            }

        return parsed_config


class AnalyzersFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(AnalyzersConfigHandler(component_name))

    def create_component(self, config, context=None):
        analyzers = []
        for analyzer_name in config:
            analyzer_config = config[analyzer_name]
            wrapper = Wrapper(
                home=analyzer_config['wrapper_home'],
                analyzer_name=analyzer_name,
                args=analyzer_config['args'],
                storage_dir=analyzer_config['storage_dir'],
                timeout_sec=analyzer_config['timeout_sec']
            )
            analyzers.append(Analyzer(wrapper))

        return analyzers
            
