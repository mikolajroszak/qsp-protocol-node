def mk_args(config):
    gas = config.default_gas
    gas_price = config.default_gas_price

    if gas is None:
        args = {'from': config.account, 'gasPrice': gas_price}
    else:
        gas_value = int(gas)
        if gas_value >= 0:
            args = {'from': config.account, 'gas': gas_value, 'gasPrice': gas_price}
        else:
            raise ValueError("The gas value is negative: " + str(gas_value))

    return args
