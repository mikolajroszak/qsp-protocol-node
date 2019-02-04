from utils.eth.singleton_lock import SingletonLock


def safe_transact(contract_entity, tx_args):
    """
    The contract_entity should already be invoked, so that we can immediately call transact
    """
    try:
        SingletonLock.instance().lock.acquire()
        return contract_entity.transact(tx_args)
    except Exception as e:
        print("!!!!!!! Safe transaction in tests failed")
        raise e
    finally:
        try:
            SingletonLock.instance().lock.release()
        except Exception as error:
            print("Error when releasing a lock in test {0}".format(str(error)))
