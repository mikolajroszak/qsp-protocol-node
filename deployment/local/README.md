## Running QSP Node Locally

This folder contains the scripts and instructions necessary for 
a node operator to spin up a QSP node.

The node runs as a Docker container. The image is hosted on Quantstamp's private repository.
The steps assume a Unix-like operating system.

**Note**: all commands should be run from the location of this README document. All paths are relative to this
README's folder.

### Install dependencies

1. Install `make`, if not already installed.
    - Verify: `make -v` should print a version `GNU Make <version> ...`.
1. Install Docker CE: https://www.docker.com/community-edition
    - Verify: `docker -v` should return `Docker version 17.09.0-ce` or above
1. On Linux environments, check the group owner of `/var/run/docker.sock`.
Add the current user to that group (generally `docker` or `root`):

    `sudo usermod -a -G <group owner of docker.sock> <username>`

The step above is required for running analyzer containers from the audit node container.

1. Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/installing.html.
    - Verify: typing `aws` should output:
        ```
        usage: aws [options] <command> <subcommand> [<subcommand> ...] [parameters]
        To see help text, you can run:

        aws help
        aws <command> help
        aws <command> <subcommand> help
        aws: error: the following arguments are required: command
        ```

### Create an Ethereum account

- Go to https://www.myetherwallet.com
- Click on the tab named "New Wallet"
- Follow the instructions. Give a strong passphrase
- Make sure to save "Keystore / JSON file" into the `keystore` subfolder of this README's location
- Add some Ether to your account (to cover gas costs)

Record for next steps:
- Your public Ethereum address, e.g., `0x60463b7ee0c3d33def3a05313597b1300f6de62b`
- The passphrase for your key
- Location of your keystore (JSON) file, e.g., `./keystore/default.json`. The location is
relative to this README's folder.

### Get whitelisted

Contact Quantstamp (the Protocol team) to whitelist your Ethereum address and generate AWS credentials for your account.

Record for next steps:
- AWS access key id, e.g., `AKIAIOSFODNN7EXAMPLE`
- AWS secret access key, e.g., `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- If provided, Ethereum node token, e.g., `8a7b2d9f0e0b9e7a6a7b8a7b2d9f0e0b9e7a6a7b8a7b2d9f`

### Configure

1. Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to the provided AWS credentials. Alternatively, do `aws configure` to specify them at the user level: when prompted, use `us-east-1` as *Default region name* and leave `None` as *Default output format*
1. Set environment variable `ENV` to `testnet` (default) or `betanet`
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
        id: !!str "0x60463b7ee0c3d33def3a05313597b1300f6de62b"
        keystore_file: !!str "./keystore/default.json"
    ```
    You account must be prefixed with `0x` and be in a checksum format.

1. Configure other settings as necessary, e.g., `gas_price`.

### Start the docker daemon

To be able to run the audit node container, one must check whether the docker daemon
is up and running (`ps -A | egrep docker`). If not running, please start it.

### Pull the latest version

`make download`. **Note**: if you need to run a specific version, in `Makefile`, edit the `IMAGE` setting by appending a digest or specifying a different tag (the default is `develop`).

### Run

`make run`
