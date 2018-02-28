def mk_args(config):
    gas = config.default_gas

    if gas is None:
        args = {'from': config.account}
    else:
        args = {'from': config.account, 'gas': int(gas)}
    
    return args