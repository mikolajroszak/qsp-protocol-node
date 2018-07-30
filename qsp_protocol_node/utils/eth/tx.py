def mk_args(config):
    gas = config.gas
    gas_price_wei = config.gas_price_wei

    if gas is None:
        args = {'from': config.account, 'gasPrice': gas_price_wei}
    else:
        gas_value = int(gas)
        if gas_value >= 0:
            args = {'from': config.account, 'gas': gas_value, 'gasPrice': gas_price_wei}
        else:
            raise ValueError("The gas value is negative: " + str(gas_value))

    return args


def send_signed_transaction(config, transaction, attempts=10):
    args = mk_args(config)
    if config.account_private_key is None:  # no local signing (in case of tests)
        return transaction.transact(args)
    else:
        nonce = config.web3_client.eth.getTransactionCount(config.account)
        for i in range(attempts):
            try:
                args['nonce'] = nonce
                tx = transaction.buildTransaction(args)
                signed_tx = config.web3_client.eth.account.signTransaction(tx,
                                                                           private_key=config.account_private_key)
                return config.web3_client.eth.sendRawTransaction(signed_tx.rawTransaction)
            except ValueError as e:
                if i == attempts - 1:
                    config.logger.debug("Maximum number of retries reached. {}"
                                        .format(e))
                    raise e
                elif "replacement transaction underpriced" in repr(e):
                    config.logger.debug("Another transaction is queued with the same nonce. {}"
                                        .format(e))
                    nonce += 1
                elif "known transaction" in repr(e):
                    # the de-duplication is preserved and the exception is re-raised
                    config.logger.debug("Transaction deduplication happened. {}".format(e))
                    raise e
                else:
                    config.logger.error("Unknown error while sending transaction. {}".format(e))
                    raise e
