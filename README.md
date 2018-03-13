# qsp-network-audit

![Build status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiRGFyS3IwWW9yVlRPcFFHOUJiYldNWjJuVi9JRmx1VUMwSUhpaGlDcmtQTnpYdThvcVRUNVQ0QktZakl6MlZYcWoveURQSkE4YThjYVdDY2lla0k3R1hvPSIsIml2UGFyYW1ldGVyU3BlYyI6ImFMMmtlWTRQdWl6Q2c3UksiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop)

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
1. Acquire AWS credentials for accessing S3 and Docker repository
1. Follow the steps [How to configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration)

## Run tests locally

1. Run `make test`

## Run in regular mode

1. Acquire a passphase of a QSP network account and set environment variable `QSP_PASSWORD` to it.
1. `make run`

## Run in container mode

1. `$(aws ecr get-login --region us-east-1 --no-include-email)`
1. `docker build -t qsp-network-audit .`
1. Acquire a passphase of a QSP network account
1. `docker run -i -t -e ENV=local_docker -e QSP_PASSWORD=passphrase-from-the-last-step qsp-network-audit`

To run a Bash shell inside the container, run it as: `docker run <other args> qsp-network-audit bash`

## Contribute 

1. Checkout a branch off `develop`
1. Make changes, open a pull request from your branch into `develop`
1. On merge into `develop`, a new Docker image is built and tagged with the commit id. 

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

