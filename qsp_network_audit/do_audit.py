from web3 import Web3, HTTPProvider
from utils.io import fetch_file, load_json

import sys

metadata = load_json(
    fetch_file("https://s3.amazonaws.com/qsp-network-contract-abi-dev/QuantstampInternal.meta.json")
)
abi = load_json(
    fetch_file("https://s3.amazonaws.com/qsp-network-contract-abi-dev/QuantstampInternal.abi.json")
)

addr = metadata['contractAddress']
w3 = Web3(HTTPProvider("http://ec2-52-91-149-89.compute-1.amazonaws.com:8545"))

account = "0xdbc1dc08bd84175c3a1a6daa2bc56f09b7469418"
passwd = "bhd9ubDsPLNYaLuH34s9E4BrvSDA5L"

# Proceed to unlock the wallet account
unlocked = w3.personal.unlockAccount(
    account,
    passwd,
    600,
)

if not unlocked:
    print("Cannot unlock wallet")
    sys.exit(1)

buggy_contract = "https://s3.amazonaws.com/qsp-network-test-contracts-dev/dao-test-13.sol"

contract = w3.eth.contract(
    abi, 
    addr,
)

# Request audit
tx = contract.transact({'from': account, 'gas': 300000}).doAudit(
    1245,
    account,
    buggy_contract,
    100,
)

print("===> doAudit submitted: " + str(tx))