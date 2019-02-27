import utils.io as utils_io

from component import BaseConfigHandler
from component import BaseComponentFactory

from validator_collection import checkers

class QSPContractConfigHandler(BaseConfigHandler):

    def __init__(self, component_name):
        super().__init__(component_name)

    def parse(self, config, config_type, context=None):
        super().parse(config, config_type, context)

        expected = set({"uri", "metadata"})
        found = set(config.keys())

        BaseConfigHandler.raise_err(
            found != expected,
            "{0} expects {1} attributes, but found {2} instead".format(
                self.component_name,
                    expected,
                    found
                )
        )

        BaseConfigHandler.raise_err(
            checkers.is_url(config['uri']),
            "Invalid URI: {0}".format(config['uri'])
        )

        BaseConfigHandler.raise_err(
            checkers.is_url(config['uri']),
            "Invalid URI: {0}".format(config['metadata'])
        )

        major_version = context.config_vars.get('major_version', 0)

        return {
            'uri': config['uri'].replace(
                '${major_version}', 
                major_version
            ),
            'metadata': config['metadata'].replace(
                '${major_version}',
                major_version
            )
        }

class QSPContractFactory(BaseComponentFactory):
    def __init__(self, component_name):
        super().__init__(QSPContractConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates the audit contract from ABI.
        """
        abi_file = utils_io.fetch_file(config['uri'])
        abi_json = utils_io.load_json(abi_file)

        metadata_file = utils_io.fetch_file(config['metadata'])
        metadata_json = utils_io.load_json(metadata_file)
        contract_address = metadata_json['contractAddress']

        return context.web3_client.eth.contract(
            address=contract_address,
            abi=abi_json,
        )

