####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from web3 import Web3


def to_checksum_address(address):
    return Web3.toChecksumAddress(address)


def is_address(address):
    return Web3.isAddress(address)


def is_checksum_address(address):
    return Web3.isChecksumAddress(address)


def mk_checksum_address(address):
    if address is None:
        return None

    if not is_address(address):
        raise ValueError("Argument {0} is not a valid address".format(address))

    if not is_checksum_address(address):
        return to_checksum_address(address)

    return address
