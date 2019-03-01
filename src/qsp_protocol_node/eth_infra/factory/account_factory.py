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

class AccountFactoryConfigHandler(BaseConfigHandler):
    def __init__(self, component_name):
        super().__init__(component_name)


class AccountFactory(BaseConfigComponentFactory):
    def __init__(self, component_name):
        super().__init__(AccountFactoryConfigHandler(component_name))

    def create_component(self, config, context=None):
        """
        Creates an Account component
        """
        try:
            address = context.config_vars['account_address']
            passwd = context.config_vars['account_passwd']

            with open(context.config_vars['keystore_file']) as keyfile:
                encrypted_key = keyfile.read()
                private_key = web3_client.eth.account.decrypt(
                    encrypted_key,
                    passwd
                )
            return Account(address, passwd, private_key)
        except Exception as exception:
            raise ConfigurationException(
                "Error reading or decrypting the keystore file '{0}': {1}".format(
                    keystore_file,
                    exception
                )
            )
