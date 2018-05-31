# qsp-protocol-node

![Build status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoib0RlSkZ0M0I5aGZVKzNYS2lyWnFaaEhJTlR0ZlpSTHU5YkwxbUFYQS8zY1AwZTVwQ0Y2cGJqTHA0ZllHMzhhMlpvV1lYdlJweWcwZ2MyQWpXUS9UYWJjPSIsIml2UGFyYW1ldGVyU3BlYyI6IitaMjBqcUVneSt6MlZmWVUiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop)

Implements the QSP audit node in the Quantstamp network.

## Development setup

All instructions must be run from the project's root folder.

1. Clone the repo
1. Run the following instructions (done once):
  ```
  brew install pyenv
  brew install pyenv-virtualenv
  pyenv install 3.6.4
  echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"\nfi' >> ~/.bash_profile
  pyenv virtualenv env
  pip install -r requirements.txt
  ```
1. Acquire AWS credentials for accessing S3 and Docker repository. If you don't have permissions to create credentials, contact the `#dev-protocol` Slack channel.
1. Follow the steps [How to configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration)
**On Mac**: double-check that Python bin path in your $PATH variable does not use the `~` character. If it does, replace it with your `/Users/<username>` (or `make` won't find `aws`).
1. Install Docker: https://docs.docker.com/install/
1. Make sure your user is a part of the docker group: `sudo usermod -a -G docker <username>`

### Run tests

1. For testing purposes, one must install the Z3 solver wrapper and the Web3 experimental tester (done once):

```
pip install z3-solver
pip install web3[tester]
```

2. Run `make test`. To access the HTML coverage report, after running tests, open `htmlcov/index.html`.

## Run in regular mode

1. Acquire a passphrase for the Ropsten test account (message the channel `#dev-protocol`) and set environment variable `ETH_PASSPHRASE`.
1. `make run`

## Run in container mode

1. Acquire a passphrase for the Ropsten test account (message the channel `#dev-protocol`) and set environment variable `ETH_PASSPHRASE`.
1. `make run-docker`

## Run tests in container mode

1. `make test-docker`

## CI and deployment pipeline

1. On every push to the repository, `buildspec-ci.yml` is activated.
The build environment is based on the modification of the Oyente image (`Dockerfile.base`),
however, this will change.
The script runs `make test` and reports the status back to AWS CodeBuild.

1. On every merge into `develop`, `buildspec.yml` is activated. It builds the image,
pushes it to AWS Docker repository, creates a build artifact (a ZIP containing 
`Dockerrun.aws.json` and `.ebextensions` from `deployment/aws-elasticbeanstalk`) and deploys it to a dev environment on AWS using
[AWS CodePipeline](https://console.aws.amazon.com/codepipeline/home?region=us-east-1#/view/qsp-protocol-node-dev).

1. To promote a dev environment to production, go to [Application versions](https://us-east-1.console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/application/versions?applicationName=qsp-protocol-node), select the desired artifact, click `Deploy`, and select `qsp-protocol-node-prod` in the dropdown.

1. To add a new deployment method, add another subfolder to `deployment`.

## SSH to instance and container
1. Go [EC2 Dashboard](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:sort=tag:Name)
1. Look for one of the instances named `qsp-protocol-node-{stage}`
1. Click `Connect` and provide the corresponding key
1. `sudo su`
1. `docker ps`, locate the image `466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-protocol-node` and record its id, e.g., `e237a5cf55f2`
1. `docker exec -i -t e237a5cf55f2 bash`

## Development hierarchy 

* Main file: `qsp_protocol_audit.py`

* Target environments are defined in `config.yaml`

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
1. Run the node [in regular mode](#run-in-regular-mode) and check if there are any issues
1. In case of significant changes, run the node [in container mode](#run-in-container-mode) and check if there are any issues
1. Open a pull request from your branch into `develop`
1. Wait for CI tests to finish and pass
1. After approved, merge into `develop`, a new Docker image is built and tagged with the commit id and deployed to [AWS](https://console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/environment/dashboard?applicationName=qsp-protocol-node&environmentId=e-c2cqj8usi7)

## Analyzer release process

Not all analyzers are easy-to-build and easy-to-run out of the box.
However, maintaining private forks is labour- and time-consuming process.
Here are the manual steps that were followed to release the analyzers.
They could be automated in the future.

### Oyente

1. Clone the latest https://github.com/melonproject/oyente
2. In `Dockerfile`, replace `pip install requests web3` with `pip install requests web3==3.16.5` (won't be necessary after https://github.com/melonproject/oyente/issues/331 is addressed)
3. In `Dockerfile`, remove the lines starting `apt-get install yarn` (won't be necessary after https://github.com/melonproject/oyente/issues/332 is addressed)
4. Login to Docker: `$(aws ecr get-login --region us-east-1 --no-include-email)`
5. Build the image `docker build -t 466368306539.dkr.ecr.us-east-1.amazonaws.com/melonproject-oyente:{commit-id} .`
6. Push the image: `docker push 466368306539.dkr.ecr.us-east-1.amazonaws.com/melonproject-oyente:{commit-id}`
