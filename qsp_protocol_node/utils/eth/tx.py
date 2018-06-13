def mk_args(config):
    gas = config.default_gas

    if gas is None:
        args = {'from': config.account, 'gasPrice': 0}
    else:
        args = {'from': config.account, 'gas': int(gas), 'gasPrice': 0}

    return args
