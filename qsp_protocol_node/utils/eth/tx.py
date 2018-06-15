def mk_args(config):
    gas = config.default_gas

    if gas is None:
        args = {'from': config.account, 'gasPrice': 0}
    else:
        gas_value = int(gas)
        if gas_value >= 0:
            args = {'from': config.account, 'gas': gas_value, 'gasPrice': 0}
        else:
            args = {'from': config.account, 'gasPrice': 0}

    return args
