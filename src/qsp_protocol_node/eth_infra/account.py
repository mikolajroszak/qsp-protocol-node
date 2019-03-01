from component import BaseConfigComponent

class Account(BaseConfigComponent):

    def __init__(self, address, passwd, private_key):
        super().__init__({'address': address, 'passwd': passwd, 'private_key': private_key})

