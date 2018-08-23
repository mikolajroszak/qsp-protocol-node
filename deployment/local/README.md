## Running QSP Node Locally

This folder contains the scripts and instructions necessary for 
a node operator to spin up a QSP node.

The node runs as a Docker container.
The steps assume a Unix-like operating system, 
and has been tested on Mac OS High Sierra 10.13.4, 
Ubuntu 18.04 and 16.04, Debian 9, and Redhat Enterprise Server 7.5.

**Note**: all commands should be run from the location of this README document. 
All paths are relative to this README's folder.

### Install and configure Docker

1. Install Docker CE: https://www.docker.com/community-edition
    - Verify: `docker -v` should return `Docker version 17.09.0-ce` or above
1. On Linux environments, check the group owner of `/var/run/docker.sock`.
Add the current user to that group (generally `docker` or `root`):

    `sudo usermod -a -G <group owner of docker.sock> <username>`

This is required for running analyzer containers from the audit node container.

To force the new group assignment to take effect, restart you session (e.g., by logging out and logging in).

### Create an Ethereum account

- Go to https://www.myetherwallet.com
- Click on the tab named "New Wallet"
- Follow the instructions. Give a strong passphrase
- Make sure to save "Keystore / JSON file" into the `keystore` subfolder of this README's location
- Add some Ether to your account (to cover gas costs)

Record for next steps:
- Your public Ethereum address, e.g., `0x60463b7Ee0c3D33deF3A05313597B1300F6dE62B`
- The passphrase (or *wallet password*) for your key
- Location of your keystore (JSON) file, e.g., `./keystore/default.json`. The location is
relative to this README's folder.

### Get whitelisted

Contact Quantstamp (the Protocol team) to whitelist your Ethereum address and generate AWS credentials for your account.

Record for next steps:
- AWS access key id, e.g., `AKIAIOSFODNN7EXAMPLE`
- AWS secret access key, e.g., `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- If provided, Ethereum node token, e.g., `8a7b2d9f0e0b9e7a6a7b8a7b2d9f0e0b9e7a6a7b8a7b2d9f`

### Configure

1. Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to the provided AWS credentials.
1. Set environment variable `ETH_PASSPHRASE` to your account's passphrase (or *wallet password*)
1. In `config.yaml`, specify the endpoint to the Ethereum node you want the QSP audit node to connect to. If connecting to Quantstamp's Ethereum secure node, just rely on the default provider endpoint:
    ```
    eth_node:
        provider: !!str "HTTPProvider"
        args:
            endpoint_uri: !!str "https://rpc.blockchaindevlabs.com/?token=${token}"
    ```
    The environment `ETH_AUTH_TOKEN` is injected in the URL, binding it to
    the `${token}` variable. If that is the endpoint to use,  please
    request an authorization token from Quantstamp.

1. In `config.yaml`, edit the `account` section to specify your account id and, if different from default, the associated keystore file path:
    ```
    account:
        id: !!str "0x60463b7Ee0c3D33deF3A05313597B1300F6dE62B"
        keystore_file: !!str "./keystore/default.json"
    ```
    You account must be prefixed with `0x` and be in **checksum** format.
    To get a checksum address, go to `https://etherscan.io/address/{your-account}` and copy the value of `Address` field on the page (it will contain some capital letters)

1. Configure other settings as necessary, e.g., `gas_price`.

### Start the docker daemon

To be able to run the audit node container, one must check whether the docker daemon
is up and running (`ps -A | egrep docker`). If not running, please start it.

### Run

`./run.sh`
