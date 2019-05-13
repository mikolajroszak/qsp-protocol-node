# qsp-protocol-node

[![Build Status](https://travis-ci.com/quantstamp/qsp-protocol-node.svg?token=99JaZsF6mzdz1szXGqFH&branch=develop)](https://travis-ci.com/quantstamp/qsp-protocol-node)

Implements the QSP audit node in the Quantstamp network. This guide presents
steps on how to perform common development tasks. For Node operators, please refer to the document ["How to become a node operator"](./doc/node-operator.md) instead.

## Requirements

1. Install Docker: <https://docs.docker.com/install/>

1. **On Linux-based Systems**: Make sure your user is a part of the docker group:

    ```bash
    sudo usermod -a -G docker <username>
    ```
    
1. Ensure node's account has enough funds. At all times, the node must have
   enough ether to pay for its associated gas fees (e.g., when bidding,
   submiting a report, etc.). When running the node against `testnet` (default), one should mint ether.

   Go to a [Ropsten faucet](https://faucet.ropsten.be/) and transfer testing ether
   to the node's target account (default is `0x60463b7ee0c3d33def3a05313597b1300f6de62b`).

1. Replace the contents of default keystore json file in `resources/keystore`
   directory with a valid keystore file.
   
1. Configure Ethereum node's authentication token. To use Infura as a provider (default),
   sign up on https://infura.io/register, create a new project, and then check the associated endpoint, e.g., `https://mainnet.infura.io/v3/abcdefg`.
   The last part of the URL (`abcdefg`) is the authentication token. Set the environment variable `QSP_ETH_AUTH_TOKEN` to the token:

   `export QSP_ETH_AUTH_TOKEN=abcdefg`

   To use a different provider, modify `eth_node/args/endpoint_uri` in
   `config.yaml` accordingly.

## Running the node

```bash
make run
```

This runs the node against `testnet`. It relies on default values for
`QSP_ETH_AUTH_TOKEN` and `QSP_ETH_PASSPHRASE`, two mandatory environment
variables used by the node. Specifically:

* `QSP_ETH_AUTH_TOKEN`: Ethereum node's
   authentication token (e.g., one obtained for Infura, a proxy node, etc).
   
* `QSP_ETH_PASSPHRASE`: passphrase of the target Ethereum account. 
The password must **NOT** contain
quotes (double or single). The safest approach to verify whether your password matches what you have set is to check
the value of `QSP_ETH_PASSPHRASE` in a terminal:
    ```
    echo $QSP_ETH_PASSPHRASE
    ```
   If the output matches your original password, the latter is correctly set.
   Otherwise, launching the audit node will fail.

Additionally, the node relies on the configuration settings given in a 
yaml file (default is `resources/config.yaml`).

## Using custom accounts

To run the node with an account different from the one given as default,
create a new account (e.g., using MyEtherWallet). 

Record the passphrase and the new Ethereum account address, storing the keystore file in an accessible
location. Change the keystore location in the yaml configuration file.


### Running tests

```bash
make test
```

### Run node's standalone report encoder

1. To encode an existing json report to a compressed hexstring, create a new container and mount the json report

```
docker run -v <file-to-mount>:<mount-location> -it <qsp-protocol-node-image> ./bin/codec -e <mount-location>
```

2. To decode a compressed hexstring, do (for example)

```
make interactive
...
/app # ./bin/codec -d 2003b7f55bc69671c5f4fb295fd5acf1375eb7f1363093176f4bec190c39f95c235b0c00190d001905001d0300190700191a0019150010120018120014
2019-01-30 15:57.56 Decoding report 0
{'audit_state': 4,
 'contract_hash': 'B7F55BC69671C5F4FB295FD5ACF1375EB7F1363093176F4BEC190C39F95C235B',
 'status': 'success',
 'version': '2.0.1',
 'vulnerabilities': [('unprotected_ether_withdrawal', 25, 25),
                     ('call_to_external_contract', 25, 25),
                     ('reentrancy', 29, 29),
                     ('transaction_order_dependency', 25, 25),
                     ('exception_state', 25, 25),
                     ('reentrancy_true_positive', 25, 25),
                     ('missing_input_validation_true_positive', 16, 16),
                     ('missing_input_validation', 24, 24),
                     ('missing_input_validation', 20, 20)]}
```

Note that there is no `0x` prefixing the hexstring.

### Run node locally and in an isolated environment

For certain use cases, it is important to run the node in such a way that it doesn't affect
any other nodes. Currently, the steps are as follows:

1. In the audit contract repository, follow the [steps](https://github.com/quantstamp/qsp-protocol-audit-contract#deploy-to-ropsten-or-main-net-through-metamask) to 
deploy the smart contracts to a separate stage (e.g., "betanet-test-123"). 

1. In `resources/config.yaml`, replace the contract addresses to point to the new stage, e.g., replace:
`https://s3.amazonaws.com/qsp-protocol-contract/dev/QuantstampAudit-v-{major-version}-abi.json`
with 
`https://s3.amazonaws.com/qsp-protocol-contract/betanet-test-123/QuantstampAudit-v-{major-version}-abi.json`.
Do it for all the contract URIs.

1. Run the node.

### Run node locally to produce a report for a given contract

This allows one to produce a non-compressed audit report for a given solidity file.

1. Copy the solidity file into the project directory (this ensures it will be included in the produced docker image).
1. Run `make interactive`.
1. Within the docker shell, run `./create_report path/to/file.sol`


## Optional features

The node allows full report uploading to a remote site (e.g., S3), as well as log streaming (e.g., CloudWatch). Currently, 
this is restricted to AWS services. The configuration steps are as follows:

1. Set up AWS credentials. If you don't have permissions to create credentials, contact the `#dev-protocol` Slack channel.

1. Follow the steps [How to configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration)  
**On Mac**: double-check that python is in your `$PATH` and its directory does not start with `~`. If it does, replace it with your `/Users/<username>` (or `make` won't find `aws`).

1. [Create an s3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/gsg/CreatingABucket.html) in your AWS account

1. Specify AWS credentials as environment variables, namely `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. 
Make sure that the AWS role has [correct permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_examples_s3_rw-bucket.html) to access the bucket. 

1. Update the following parameters under `upload_provider` in `config.yaml`:
    1. `bucket_name`
    1. `contract_bucket_name`

1. Additionally, one can also [stream logs to CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html). Once AWS credentials are in place, simply enable `logging/streaming` in
 `resources/config.yaml`, changing the following default parameters (if desired):
    1. `log_group`
    1. `log_stream`

## To start developing

* If you want to build locally just run `make build` 
For full instructions, please review  [developer's documentation]

## Troubleshooting

This section includes situations that a command previously failed and we came up with ways to mitigate it. The following troubleshooting statements are in the form below:

While _`doing command`_, on _`environment`_, we encountered _`this message`_, then _`did these steps`_.

(OPTIONAL) Visualize logs :

You can use ELK stack to visualize logs or aggregate results for troubleshooting.

1. Make sure docker daemon is running
2. Run `make elk`
5. Access kibana dashboard from a browser on port 5601
6. Create a new index pattern under management matching logstash*. (this can take a couple of minutes while logstash comes online).
7. For timestamp select `@timestamp`.
8. Now visit discover tab to see the logs. 

To learn more about ELK please visit https://www.elastic.co/learn
