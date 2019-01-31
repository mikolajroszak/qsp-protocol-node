# qsp-protocol-node

![Build status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiZDlrWUpGTmt1Y0RsdXpvbVdOdHhNUlVxWjlkYnd3VXBsbDBhRXc0RGg0S2FCOEpxaTBhbHpGRDRjSm5OTDE1S0laQnViU1JTVW1ZODJ5NUMxSHdnTzc0PSIsIml2UGFyYW1ldGVyU3BlYyI6IlpIRFRacVlPcUF3S1EybmoiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop)

Implements the QSP audit node in the Quantstamp network. This guide presents
steps on how to perform common development tasks.

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

1. Configure Ethereum node's authentication token. To use Infura as a provider (default),
   sign up on https://infura.io/register, create a new project, and then check the associated endpoint, e.g., `https://mainnet.infura.io/v3/abcdefg`.
   The last part of the URL (`abcdefg`) is the authentication token. Set the environment variable `QSP_ETH_AUTH_TOKEN` to the token:

   `export QSP_ETH_AUTH_TOKEN=abcdefg`

   To use a different provider, modify `eth_node/args/endpoint_uri` in `config.yaml` accordingly.

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
yaml file (default is `deployment/local/config.yaml`).

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
docker run -v <file-to-mount>:<mount-location> -it <qsp-protocol-node-image> ./codec -e <mount-location>
```

2. To decode a compressed hexstring, do (for example)

```
make interactive
...
/app # ./codec -d 2003b7f55bc69671c5f4fb295fd5acf1375eb7f1363093176f4bec190c39f95c235b0c00190d001905001d0300190700191a0019150010120018120014
2019-01-30 15:57.56 Decoding report 0
{'audit_state': 4,
 'contract_hash': 'B7F55BC69671C5F4FB295FD5ACF1375EB7F1363093176F4BEC190C39F95C235B',
 'status': 'success',
 'version': '2.0.0',
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
deploy the smart contracts to a separate stage (e.g., "betanet-test-123"). Do the necessary whitelisting.

1. In `deployment/local/config.yaml`, replace the contract addresses to point to the new stage, e.g., replace:
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

1. Update the following paramters under `report_uploader` in `config.yaml`:
    1. `bucket_name`
    1. `contract_bucket_name`

1. Additionally, one can also [stream logs to CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html). Once AWS credentials are in place, simply enable `logging/streaming` in
 `deployment/local/config.yaml`, changing the following default parameters (if desired):
    1. `log_group`
    1. `log_stream`

## CI and deployment pipeline

1. On every push to the repository, `buildspec-ci.yml` is activated. The build script runs `make test-ci` and reports the status back to AWS CodeBuild.

1. On every merge into `develop`, `buildspec.yml` is activated. It builds the image, pushes it to AWS Docker repository, creates a build artifact (a ZIP containing `Dockerrun.aws.json` and `.ebextensions` from `deployment/aws-elasticbeanstalk`) and deploys it to a dev environment on AWS using [AWS CodePipeline](https://console.aws.amazon.com/codepipeline/home?region=us-east-1#/view/qsp-protocol-node-dev).

1. To promote a dev environment to production (automation is coming as part of `QSP-488` - "Create staging (dev -> prod) pipeline for safe release to production"):
    1. In dev AWS account, go to [Application versions](https://us-east-1.console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/application/versions?applicationName=qsp-protocol-node), download the desired artifact and unzip it
    2. Download the Docker image referenced in the unzipped folder's `Dockerrun.aws.json` and re-push it to the prod account id
    3. Edit `Dockerrun.aws.json` to use the prod AWS account id instead of the dev account id
    4. Zip the files located inside extracted folder. Note: do not zip the containing folder, only the files
    5. Run `zip -d Archive.zip __MACOSX/\*` to remove MacOS files from the archive
    6. In prod account's AWS console, upload the ZIP to the Beanstalk environment

1. To add a new deployment method, add another subfolder to `deployment`.
1. The [end-to-end test](https://console.aws.amazon.com/codepipeline/home?region=us-east-1#/view/qsp-protocol-end-to-end-test-dev) runs periodically against the Dev stack and posts any failures to the channel `#qsp-monitoring-dev`. To run the test outside of the regular schedule, go to the test link and do `Release change`.

1. [Audit node logs](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:group=/aws/elasticbeanstalk/qsp-protocol-dev/all.log)

## SSH to instance and container

1. Go [EC2 Dashboard](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:sort=tag:Name)

1. Look for one of the instances named `qsp-protocol-node-{stage}`

1. Click `Connect` and provide the corresponding key

1. Type in the following commands:

    ```bash
    sudo su
    docker ps
    ```

    and locate the image `466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-protocol-node` and record its id, e.g., `e237a5cf55f2`.
    With that, run:

    ```bash
    docker exec -i -t e237a5cf55f2 bash
    ```

## Creating a Betanet distribution bundle

Currently, the process is mostly manual. To be automated in the future.

### Release
1. Run `make bundle`. If successful, this  will create `qsp-protocol-v1.zip` file under deployment/local.
1. Upload the file to Google Drive (`QSP Protocol V1 - Release Bundles`)
1. Using Google Drive sharing features, share the file with a whitelisted node operator

## Development hierarchy

* Main file: `qsp_protocol_node/__main__.py`

* Target environments are defined in `deployment/local/config.yaml`

* QSPAuditNode gets params from YAML
  - `config.py`
    - provides an interface for accessing configured components
    instantiated from the settings in the YAML file
  - `audit.py`
    - main loop is in the run() method
    - logic for audit computation
    - report is JSON and posted to Ethereum
  - `analyzer.py`
    - abstracts an analyzer tool
    - needs to accept parameters in a better way

## Contribute

1. Checkout a branch off `develop`

1. Make changes

1. Run `make test`. Fix any issues or update the tests if applicable

1. [Run the node](#run-locally) and check if there are any issues

1. Open a pull request from your branch into `develop`

1. Wait for CI tests to finish and pass

1. After approval, merge into `develop`, a new Docker image is built and tagged with the commit id and deployed to [AWS](https://console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/environment/dashboard?applicationName=qsp-protocol-node&environmentId=e-c2cqj8usi7)

## Codestyle

The codestyle builds on PEP8 and includes especially the following:

1. Indentation is done using spaces in multiples of 4
2. Lines are broken after 100 characters, longer lines are allowed in exceptional cases only
3. Methods are separated with 2 blank lines
4. Do not use parentheses when not necessary
5. `import` statements come before `from import` statements
6. Import only one module per line
7. Remove unused imports
8. Use lowercase_underscore naming for variables
9. Use `is` and `is not` when comparing to `None`
10. Beware of overriding built-ins

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
