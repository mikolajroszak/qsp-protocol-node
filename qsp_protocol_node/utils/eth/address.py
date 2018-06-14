def mk_checksum_address(web3, address):
    if address is None:
        return None

    if not web3.isAddress(address):
        raise ValueError("Argument {0} is not a valid address".format(address))

    if not web3.isChecksumAddress(address):
        return web3.toChecksumAddress(address)

    return address
