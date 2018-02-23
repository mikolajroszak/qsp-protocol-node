# qsp-network-audit

![Build status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiUmNIbFJiY0FVOUVmdWJ2TTlyNEVRU2p2TWZ1LzhUa0o4dE9TQUFkbkhZM0FvRFRhZ0lhSzFQYXRSd3hlZEVkQWRJSFBZSFdNaHV6SnBwZEtGUXhVOTJVPSIsIml2UGFyYW1ldGVyU3BlYyI6InhWa2lSWmhmZHJkejRYWnoiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop)

Implements the QSP audit node in the Quantstamp network.

## Development setup

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

## Docker image build

**Note:** double-check the path of Oyente as it may be not consistent if
running as container or without it.

```
docker build -t qsp-network-audit .
docker run -i -t -e QSP_PASSWD=<passwd> qsp-network-audit
```

where `passwd` is the password to unlock the wallet account configured in
the `config.yaml` file.

To run a Bash shell inside the container, run it as: `docker run <other args> qsp-network-audit bash`


## Deployment

1. Checkout a branch off `develop`
1. Make changes, open a pull request from your branch into `develop`
1. On merge into `develop`, a new Docker image is built and tagged with `develop`. Previous versions are available when referenced as `466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-analyzer-oyente:<commit-id>`

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

## Running the node

Before running the node one must:

1. Set the password for unlocking the target wallet account. That is given by the `QSP_PASSWD` environment variable.
2. Configure AWS credentials to allow write access to the reports bucket on S3. On AWS, the instance's IAM role has the necessary
policies attached thus does not require to specify any credentials (recommended approach). On a local machine, use `aws configure` to provide 
AWS access keys.

With that, the node is launched by running

```
make run
```

To run the unit tests, type `make test`. 
