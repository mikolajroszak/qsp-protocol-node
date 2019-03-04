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
from eth_infra.account import Account

from json import dumps

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
        address = context.tmp_vars['keystore']['address']
        passwd = context.tmp_vars['account_passwd']
        encrypted_key = dumps(context.tmp_vars['keystore'])

        try:
            private_key = context.web3_client.eth.account.decrypt(
                encrypted_key,
                passwd
            )
            return Account(address, passwd, private_key)
        except Exception as exception:
            raise ConfigurationException(
                "Error decrypting key '{0}': {1}".format(
                    encrypted_key,
                    exception
                )
            )
