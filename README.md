# qsp-network-audit

![Build status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoib0RlSkZ0M0I5aGZVKzNYS2lyWnFaaEhJTlR0ZlpSTHU5YkwxbUFYQS8zY1AwZTVwQ0Y2cGJqTHA0ZllHMzhhMlpvV1lYdlJweWcwZ2MyQWpXUS9UYWJjPSIsIml2UGFyYW1ldGVyU3BlYyI6IitaMjBqcUVneSt6MlZmWVUiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop)

Implements the QSP audit node in the Quantstamp network.

## Development setup

All instructions must be run from the project's root folder.

1. Clone the repo
1. `git submodule init`
1. `git submodule update`
1. Run the following instructions:
  ```
  brew install pyenv
  brew install pyenv-virtualenv
  pyenv install 3.6.4
  echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"\nfi' >> ~/.bash_profile
  pyenv virtualenv env
  pip install -r requirements.txt
  ```
1. Acquire AWS credentials for accessing S3 and Docker repository. If you don't have permissions to create credentials, contact the `#ops` Slack channel.
1. Follow the steps [How to configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration)

## Run tests locally

1. Run `make test`. To access the HTML coverage report, after running tests, open `htmlcov/index.html`.

## Run in regular mode

1. Acquire a passphase of a QSP network account and set environment variable `QSP_PASSWORD` to it.
1. `make run`

## Run in container mode

1. Login to be able to acquire the base image: `$(aws ecr get-login --region us-east-1 --no-include-email)`
1. Build the image: `docker build -t qsp-network-audit .`
1. Acquire a passphase of a QSP network account
1. `docker run -i -t -e ENV=local_docker -e QSP_PASSWORD=passphrase-from-the-last-step qsp-network-audit`

To run a Bash shell inside the container, run it as: `docker run <other args> qsp-network-audit bash`

## CI and deployment pipeline

1. On every push to the repository, `buildspec-light.yml` is activated.
The build environment is based on the Oyente's image (`qsp-analyzer-oyente`).
The script runs `make test` and reports the status back to AWS CodeBuild.

1. On every merge into `develop`, `buildspec.yml` is activated. It builds the image,
pushes it to AWS Docker repository, creates a build artifact (a ZIP containing the 
`Dockerrun.aws.json` file and the `.ebextensions` folder) and deploys it toa dev environment on AWS using
[AWS CodePipeline](https://console.aws.amazon.com/codepipeline/home?region=us-east-1#/view/qsp-network-audit-dev).

1. To promote a dev environment to production, go to [Application versions](https://us-east-1.console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/application/versions?applicationName=qsp-network-audit), select the desired artifact, click `Deploy`, and select `qsp-network-audit-prod` in the dropdown.

## Infrastructure

1. The current infrastructure is based on Elastic Beanstalk and described in [this repository](https://github.com/quantstamp/qsp-network-genesis) using [Terraform](https://www.terraform.io/).
1. The next-generation infrastructure based on Kubernetes is described in [this repository](https://github.com/quantstamp/qsp-network-kubernetes).

## SSH to instance and container
1. Go [EC2 Dashboard](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:sort=tag:Name)
1. Look for one of the instances named `qsp-network-audit-{stage}`
1. Click `Connect` and provide the corresponding key
1. `sudo su`
1. `docker ps`, locate the image `466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-network-audit` and record its id, e.g., `e237a5cf55f2`
1. `docker exec -i -t e237a5cf55f2 bash`

## Development hierarchy 

* Main file: `qsp_network_audit.py`

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
1. Wait for CI tests to finish
1. On merge into `develop`, a new Docker image is built and tagged with the commit id and deployed to [AWS](https://console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/environment/dashboard?applicationName=qsp-network-audit&environmentId=e-c2cqj8usi7)
