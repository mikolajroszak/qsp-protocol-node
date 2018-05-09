class DummyWalletSessionManager:
    def unlock(self, ttl):
        pass

    def lock(self):
        pass


class WalletSessionManager:
    def __init__(self, web3_client, account, passwd):
        self.__web3_client = web3_client
        self.__account = account
        self.__passwd = passwd

    def unlock(self, ttl):
        unlocked = self.__web3_client.personal.unlockAccount(
            self.__account,
            self.__passwd,
            ttl,
        )

        if not unlocked:
            raise Exception(
                "Cannot unlock account {0}.".format(self.__account))

    def lock(self):
        self.__web3_client.personal.lockAccount(self.__account)
