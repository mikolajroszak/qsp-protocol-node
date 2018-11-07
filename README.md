# qsp-protocol-node

![Build status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiZDlrWUpGTmt1Y0RsdXpvbVdOdHhNUlVxWjlkYnd3VXBsbDBhRXc0RGg0S2FCOEpxaTBhbHpGRDRjSm5OTDE1S0laQnViU1JTVW1ZODJ5NUMxSHdnTzc0PSIsIml2UGFyYW1ldGVyU3BlYyI6IlpIRFRacVlPcUF3S1EybmoiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop)

Implements the QSP audit node in the Quantstamp network.

## Run a QSP node locally

- To build and run the node from the source code, follow the instructions from the `Development setup` section and then refer to the `Run locally` subsection.

- To test out the node operator instructions:
    - Do `make export` to export a Docker image
    - Go to `deployment/local` and follow the steps in the dedicated [README](deployment/local/README.md)

## Development setup

All instructions must be run from the project's root folder.

1. Make sure you have [`pyenv`](https://github.com/pyenv/pyenv) installed and that it is properly initialized. Initialization entails changing your `~/.bash_profile` (if not already done so):

    ```bash
    echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
    ```

    and sourcing it:

    ```bash
    source ~/.bash_profile
    ```

1. Install dependencies
    * automake
    * libtool
    * awscli
    * pyenv
    * pyenv-virtualenv
    * coreutils
    * jq

    For Mac, this can be done using `brew`:
    ```bash
    brew install automake libtool awscli pyenv pyenv-virtualenv coreutils jq
    ```

    You also need to install the compiler for Solidity 0.4.24. If not installed, this can be done with
    ```bash
    brew install https://raw.githubusercontent.com/ethereum/homebrew-ethereum/9599ce8371d9de039988f89ed577460e58a0f56a/solidity.rb
    ```

    If you have a newer version of the compiler installed together with 0.4.24, you may need to switch the default solc to be the latter kind:
    ```
    brew switch solidity 0.4.24
    ``` 

1. Clone the repo and set it up by running:

    ```bash
    make setup
    ```

1. Acquire AWS credentials for accessing S3 and Docker repository. If you don't have permissions to create credentials, contact the `#dev-protocol` Slack channel.

1. Follow the steps [How to configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration)  
**On Mac**: double-check that Python bin path in your `$PATH` variable does not use the `~` character. If it does, replace it with your `/Users/<username>` (or `make` won't find `aws`).

1. Install Docker: <https://docs.docker.com/install/>

1. **On Linux-based Systems**: Make sure your user is a part of the docker group:

    ```bash
    sudo usermod -a -G docker <username>
    ```

1. If you are using MacOS, ensure `Xcode` is installed.

### Run tests

1. For testing purposes, issue:

    ```bash
    make test
    ```

2. To access the HTML coverage report, after running tests, open `tests/coverage/htmlcov/index.html`

3. To run tests inside a container, run

```bash
make test-docker
```

### Run locally

1. Set the environment `ETH_AUTH_TOKEN` to the Ethereum node's authentication token
2. `make run`. Alternatively:
    - `make run-docker` to run as a container
    - `make run-with-auto-restart` to leverage the auto-restart feature.

This will run the node using the default (test) account for Ropsten. This is suitable for quick local run but not recommended for thorough testing.

To run with a custom account:

1. Create a new account (e.g., using MyEtherWallet). Record the passphrase, the new account Ethereum address, and store the keystore file in an accessible location
1. In `deployment/local/config.yaml/testnet/account/id`, specify the Ethereum address and in `deployment/local/config.yaml/testnet/account/keystore_file`, specify the path to the keystore file. The address must be in the **checksum** format. Example:
    ```text
    account:
      id: !!str "0x60463b7Ee0c3D33deF3A05313597B1300F6dE62B"
      keystore_file: !!str "./keystore/default.json"
    ```
1. Set the environment variable `ETH_PASSPHRASE` to the passphrase of your account. Note that your password may **NOT** contain
quotes (double or single). The safest approach to verify whether your password matches what you have set is to check
the value of `ETH_PASSPHRASE`. In a terminal, type:
    ```
    echo $ETH_PASSPHRASE
    ```
If the output matches your original password, the latter is correctly set.
Otherwise, launching the audit node will fail.
1. Whitelist the address using the [whitelist command](https://github.com/quantstamp/qsp-protocol-audit-contract#commands)
1. Transfer some Ether to the account (for Ropsten, use a Ropsten faucet)

By default, the node is pointed to the Dev stage that is on Ropsten, thus your node is competing with the node on AWS to process the audit request sent by the end-to-end test (runs every hour). If your node processes the request correctly, there will be no test failure. To run the node in an isolated environment, see the next section.

### Run Standalone Report Encoder

1. To encode an existing json report to a compressed hexstring, run

```
python3 qsp_protocol_node/audit/report_processing.py -e path/to/file/report.json
```

2. To decode a compressed hexstring, run (for example)

```
python3 qsp_protocol_node/audit/report_processing.py -d 0108A9C2343908B4A6981E34BEE55C971F2104E53973DB37A24B83810FA6347FAD06
```

Note that there is no `0x` prefixing the hexstring.

### Run locally in an isolated environment
For certain use cases, it is important to run the node in such a way that it doesn't affect
any other nodes. Currently, the steps are as follows:

1. In the audit contract repository, follow the [steps](https://github.com/quantstamp/qsp-protocol-audit-contract#deploy-to-ropsten-or-main-net-through-metamask) to deploy the smart contracts to a separate stage (e.g., "betanet-test-123"). Do the necessary whitelisting.

2. In `deployment/local/config.yaml`, replace the contract addresses to point to the new stage, e.g., replace:
`https://s3.amazonaws.com/qsp-protocol-contract/dev/QuantstampAudit-v-{major-version}-abi.json`
with 
`https://s3.amazonaws.com/qsp-protocol-contract/betanet-test-123/QuantstampAudit-v-{major-version}-abi.json`.
Do it for all the contract URIs.

3. Run the node.

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

* Main file: `qsp_protocol_audit.py`

* Target environments are defined in `deployment/local/config.yaml`

* QSPAuditNode gets params from YAML
  - `config.py`
    - provides an interface for accessing configured components
    instantiated from the settings in the YAML file
  - `audit.py`
    - main loop is in the run() method
    - logic for audit computation
    - report is JSON and posted to the private blockchain
  - `analyzer.py`
    - abstracts an analyzer tool
    - needs to accept parameters in a better way
  - security constraints
    - network audit service might have a threat of price forgery (it is possible for a contract to be audited twice?)
    - need to control the state of this service
      - uptime monitoring
      - metrics

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

> While _executing_ `pyenv install 3.6.4`, on `macOS 10.13.4`, we encountered `zipimport.ZipImportError: can't decompress data; zlib not available`, then _installed_ `xcode-select --install`.


