class Account(object):

    def __init__(self, address, passwd, private_key):
        self.__address = address
        self.__passwd = passwd
        self.__private_key = private_key

    @property
    def address(self):
        return self.__address

    @property
    def passwd(self):
        return self.__passwd

    @property
    def private_key(self):
        return self.__private_key
