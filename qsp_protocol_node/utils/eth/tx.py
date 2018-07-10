def mk_args(config):
    gas = config.default_gas
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

def send_signed_transaction(config, transaction):
    args = mk_args(config)
    private_key = None
    if config.account_keystore_file is None: # using the default account
        return transaction.transact(args)
    else:        
        args['nonce'] = config.web3_client.eth.getTransactionCount(config.account)
        tx = transaction.buildTransaction(args)    
        with open(config.account_keystore_file) as keyfile:
            encrypted_key = keyfile.read()
            private_key = config.web3_client.eth.account.decrypt(encrypted_key, config.account_passwd)
            
        signed_tx = config.web3_client.eth.account.signTransaction(tx, private_key=private_key)
        return config.web3_client.eth.sendRawTransaction(signed_tx.rawTransaction)
