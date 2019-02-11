## Running QSP Node Locally

This folder contains the scripts and instructions necessary for 
a node operator to spin up a QSP node.

The node runs as a Docker container.
The steps assume a Unix-like operating system, 
and has been tested on Mac OS High Sierra 10.13.4, 
Ubuntu 18.04 and 16.04, Debian 9, and RedHat Enterprise Server 7.5.

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
- The passphrase (or *wallet password*) for your key
- Location of your keystore (JSON) file, e.g., `./resources/keystore/default.json`. The location is
relative to this README's folder.

### Configure

1. Set environment variable `QSP_ETH_PASSPHRASE` to your account's passphrase (or *wallet password*).
Note that your password may **NOT** contain
quotes (double or single). The safest approach to verify whether your password matches what you have set is to check
the value of `QSP_ETH_PASSPHRASE`. In a terminal, type:
    ```
    echo $QSP_ETH_PASSPHRASE
    ```
If the output matches your original password, the latter is correctly set.
Otherwise, launching the audit node will fail.

1. If you would like to proceed with Infura as a back-end (default), sign up on
   https://infura.io/register, create a project, and then check the associated
   endpoint
   (something like `https://mainnet.infura.io/v3/abcdefg`). The last part of the
   URL (in our example  `abcdefg`) is the authentication token. Copy it and assign it to
   the environment variable `QSP_ETH_AUTH_TOKEN`. If you'd like to use
   your own endpoint, modify `eth_node/args/endpoint_uri` in `config.yaml` to
   the endpoint of your choice.

1. If the location of your keystore file is different from the default one, in `config.yaml`, edit the line `keystore_file: !!str "./resources/keystore/default.json"`

1. Configure other settings as necessary, e.g., `gas_price`.

### Start the docker daemon

To be able to run the audit node container, one must check whether the docker daemon
is up and running (`ps -A | egrep docker`). If not running, please start it.

### Run

`./start-node`

You can use nohup to run the script in detached mode:

`nohup ./start-node &`

### View Logs

Logs are written to `qsp-protocol-node.log` file in current directory.

### Stop

`./stop-node`

Will stop and remove the docker containers.
