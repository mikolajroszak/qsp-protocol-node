# How to become a node operator

## Overview

### Local Installation Checkbox ( related to local machine )
1. [Download the bundle](#1-download-the-bundle)
2. [Infura](#2-setting-up-infura)
    1. Create an account
    1. Created a project and obtained an `[Infura Token]`
3. [Ethereum Account (Suggesting MyEtherWallet)](#3-setting-up-an-ethereum-account)
    1. Created an account `[MyEtherWallet PublicKey]` with `[MyEtherWallet Password]` and obtained `[MyEtherWallet keystore file]`
    1. Import into MetaMask
4. [Local Machine setup](#4-local-machine-setup)
    1. Copying `[My EtherWallet keystore file]` to specified location
    1. Docker
        1. Installed on local machine
        1. Set the environment for Docker as specified

### [Making your Ethereum Account eligible as a node operator](#making-your-account-eligible-as-a-node-operator)
1. Transfer ether and QSP to `[MyEtherWallet PublicKey]`
1. Stake QSP into `[The Protocol Contract]`
    1. Approving `[The Protocol Contract]` to withdraw funds from you
    1. Initiate `[The Protocol Contract]` to freeze the funds and start staking
1. Set the minimum audit price

### [Spinning up your machine to run as a node](#running-the-node)
1. Set environment variables when using a new terminal
1. Run command: `make run`
1. Check if run correctly 

### [After running the node for a while](#after-running-the-node-for-a-while-1)
-  Checking how much QSP have you earned 
-  How to unstake your funds (Warning: not eligible to audit anymore)

## Local Installation

### 1. Download the bundle 
Download and decompress the repository from the release, the newest release can be found on the following page:  https://github.com/quantstamp/qsp-protocol-node/releases

### 2. Setting up Infura
You need an Infura account and API token for your node to be able to send transactions to the Ethereum network via the Infura API.
If you already have an Infura API token that you are using elsewhere, we recommend that you create a new token specifically for the node.

1. Visit https://infura.io
1. Login or Create an account
1. Create new project
    ![](node-operator/INFURA-01-CreateProject.png)

1. Enter project name (we entered "qsp protocol node" as an example)
    ![](node-operator/INFURA-02-ProjectName.png)
1. After creation of the project, you can see it on the dashboard
    ![](node-operator/INFURA-03-ProjectOnFirstPage.png)

1. Click `VIEW PROJECT`
    ![](node-operator/INFURA-04-ProjectDetail.png)

1. Copy the string after `mainnet.infura.io/v3/`, this is the string that we will later refer to as `[Infura Token]`

After the steps above, you should obtain:
* An Infura token

### 3. Setting up an Ethereum account

The node sends transactions to the Ethereum network. For this, it needs its own Ethereum account. We recommend that
you create a new account for the node and do not use the account elsewhere. The following instructions show how you
can create an account via MyEtherWallet, however, any Ethereum account with a valid keystore file will work fine with the node.

#### Create account via MyEtherWallet
1. Visit https://www.myetherwallet.com
1. Create a new wallet
1. Click the `By Keystore File` option, enter a password for the wallet, then click `Next`
1. After it successfully generated the Keystore File, click on `Download Keystore File`


After the steps above, you should have:
* A password that you created for the keystore, we shall refer to it as `[MyEtherWallet password]`
* A keystore file that allows you to access your account through MyEtherWallet, we shall refer to it as `[MyEtherWallet keystore file]`

Now you can try to access your account through MyEtherWallet to read you address.

1. Click `Access My Wallet`
1. Click `Software`
1. Select `Keystore` and click `continue`. A dialogue will pop up. In this dialogue, select the `[MyEtherWallet keystore file]` you just downloaded.
1. When done, type in `[MyEtherWallet password]`, then click on `"Access Wallet"`.
You should be able to see your account details, your `[Ethereum public address]` is under the `Address`


#### Import account into MetaMask
Your node will be identifying itself to the network via the account that you just created. In order to be
accepted as an auditor, you will need to stake some QSP. The instructions below will show you how to import
the account to Metamasks so that you can do so.

1. Open MetaMask

    ![](./node-operator/METAMASK-IMPORT-01-Open.png)

1. Click the upper right circle to browse `My Accounts`

    ![](./node-operator/METAMASK-IMPORT-02-ViewAccounts.png)

1. Click `Import Account`

    ![](./node-operator/METAMASK-IMPORT-03-ImportDetail.png)

1. Select Type to be `JSON File`, choose the `[MyEtherWallet keystore file]` and enter the `[MyEtherWallet password]`, then click `Import`. When done, you should be able to see that your account has been imported into MetaMask.

    ![](./node-operator/METAMASK-IMPORT-04-CheckImport.png)
    


### 4. Local machine setup
#### Setting up Docker
1. Install Docker CE: https://www.docker.com/community-edition
    Verify: `docker -v` should return Docker version 17.09.0-ce or above

1. ONLY On Linux environments (SKIP this step if you’re using MacOS), check the group owner of /var/run/docker.sock. 

    Run command: `ls -l /var/run/docker.sock` 
    ![](./node-operator/DOCKER-00-Checkgroup.png)

    The example above shows that the group owner is `staff`

1. ONLY On Linux environments (SKIP this step if you’re using MacOS), add the current user to that group (generally docker or root):
`sudo usermod -a -G <group owner of docker.sock> <username>`
This is required for running analyzer containers from the audit node container.
To force the new group assignment to take effect, restart you session (e.g., by logging out and logging in).

#### Copy the `[MyEtherWallet keystore file]` into a specific location
Copy the `[MyEtherWallet keystore file]` into `resources/keystore/default.json` in the `qsp_protocol_node` directory that you downloaded and unzipped. Replace the original `default.json` file.

## Making your account eligible as a node operator
### Transfer Ether and QSP to  `[Ethereum public address]`
The node needs Ether to be able to pay for gas when transacting with the network. We recommend that you transfer small amount into the account.
For example, 0.5 ETH would be a fully sufficient amount. We also recommend that you monitor the balance and keep the account above 0.25 ETH.

### Stake QSP into the protocol
Staking freezes some QSP funds from the node's account and makes the node eligible to perform audits.
This is to safeguard the correctness of the produced audit report and provide a disincentive for a malicious node.
If your node does not submit correct results, its stake will be slashed.

The staking amount is pre-defined and fixed, currently it is 10,000 QSP.
We will refer to this amount as `[QSP Staking Amount]` later in the document.

There are two steps to stake into the Quantstamp protocol:
1. The node operator needs to interact with the `[QSP Token Contract]` to approve `[The Protocol Contract]` to withdraw QSP.
1. The node operator will need to tell `[The Protocol Contract]` that the funds are ready to be withdrawn and frozen as a stake.

#### Approve `[The Protocol Contract]` to withdraw QSP from you
In this part, we will be interacting with the `[QSP Token Contract]` to allow staking into `[The Protocol Contract]`. You could interact with the `[QSP Token Contract]` through the website EtherScan(http://etherscan.io).

The address of `[The Protocol Contract]` can be found in the `[contractAddress]` here: 
https://s3.amazonaws.com/qsp-protocol-contract/mainnet/QuantstampAudit-v-2-meta.json

1. View `[QSP Token Contract]` on Mainnet with MyEtherScan: https://etherscan.io/address/0x99ea4db9ee77acd40b119bd1dc4e33e1c070b80d

1. Navigate to `Write Contract` in the tabs below

    ![](node-operator/ETHERSCAN-APPROVE-01-QSPContract.png)

1. If there is a `Connect with Metamask` link next to the text "Write Contract". Click it.

    ![](node-operator/ETHERSCAN-APPROVE-02-WriteContractView.png)

1. Approve its request to connect to Metamask

    ![](node-operator/ETHERSCAN-APPROVE-03-ConnectMetamask.png)

1. You should see a green circle next to the write contract after you connected ehterscan.io to your MetaMask.

    ![](node-operator/ETHERSCAN-APPROVE-04-ConnectedGreenLight.png)

1. Approve the `[The Protocol Contract]` to withdraw funds:

    1. Navigate to the `approve` function
    
        ![](node-operator/ETHERSCAN-APPROVE-05-WriteAppears.png)

    1. Fill the field `_spender` with the address of `[The Protocol Contract]`

    1. Fill the field `_value` with a number that is `[QSP Staking Amount]` multiplied by 10^18. This is similar to how ETH gets converted to Wei.

    1. Click the `Write` button

    1. Click `Confirm` to approve `[The Protocol Contract]` to withdraw funds. The 0.1 QSP here is only an example, it would be `[QSP Staking Amount]` in your case.
    
        ![](node-operator/ETHERSCAN-APPROVE-06-MetaMaskConfirm.png)

    1. You will see `View your transaction` button appear next to the `Write` button.
    
        ![](node-operator/ETHERSCAN-APPROVE-07-ViewTransactionApperas.png)

#### Tell the `[The Protocol Contract]` to freeze and stake the funds
1. Find `[The Protocol Contract]` on EtherScan using the address of `[The Protocol Contract]`.
1. Navigate to the `Write Contract` tab
1. (Since already connected in the step above, this is likely not the case and you may skip it!) If there is a `Connect with Metamask` link next to the text "Write Contract", click it. Approve its request to connect on Metamask. Then, you should see a green circle next to the write contract after you connected ehterscan.io to MetaMask.
1. Staking the funds to `[The Protocol Contract]`:
    1. Navigate to the `stake` function
    1. Fill the field amount with `[QSP Staking Amount]` multiplied by 10^18.
    1. Click the `Write` button

### Set the minimum audit price
You can set a minimum audit price as a configuration parameter. This is the minimum price in QSP for which your node will be willing to perform a scan of a smart contract submitted to the Quantstamp protocol.

Open `resources/config.yaml`. Search for `min_price_in_qsp` and change the value accordingly. Make sure that you do not change anything else in this file, including indentation.

The default setting `min_price_in_qsp: !!int 1000` indicates that the node will not execute any audit request if the reward is less than 1,000 QSP. If you wished to increase this amount to 50,000 QSP,
you would need to change the line to `min_price_in_qsp: !!int 50000`.


## Running the Node
### Setting up your local machine configuration for every new Terminal opened

You need to set two environment variables for the node to be able to connect to Infura API, and for it
to be able to send transactions from the Ethereum account that you created. Open `Terminal` and enter
the following two commands:

- `export QSP_ETH_AUTH_TOKEN="[Infura Token]"`
- `export QSP_ETH_PASSPHRASE="[MyEtherWallet Password]"`

### Run the Node!
In terminal, navigate to the folder with the Quantstamp protocol node and execute the command `make run`

### Check if you node runs correctly
1. Go to protocol.quantstamp.com 
1. Check if your `[Ethereum public address]` is in the `QSP Nodes` panel

    ![](./node-operator/RUN-NODEPANEL.png)

## After running the node for a while
### Checking how much QSP have you earned
Navigate to https://etherscan.io/address/[MyEtherWallet PublicKey], you can find the information in the Overview panel.

![](./node-operator/AFTERRUN-CHECKGAIN.png)

### How to unstake your funds (Warning: not eligible to run more scans) 
When you decide to no longer operate a Quantstamp protocol node, you might want to unstake the funds so that they are returned to the node's account. Here are the steps to unstake your funds:

1. Find `[The Protocol Contract]` on the website EtherScan using The address of `[The Protocol Contract]`.
1. Navigate to the `Write Contract` tab
1. If there is `Connect with Metamask` next to the text "Write Contract", click it. If not, skip this step. Approve its request to connect to Metamask. Then, you should see a green circle next to the write contract after you connected ehterscan.io with MetaMask.
1. Unstake the funds from `[The Protocol Contract]`:
    1. Navigate to the unstake function
    1. Click the `Write` Button

