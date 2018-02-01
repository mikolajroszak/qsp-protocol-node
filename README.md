# qsp-network-audit
Implements the QSP audit node in the Quantstamp network

## Development

```
brew install pyenv
brew install pyenv-virtualenv
pyenv install 3.6.4
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"\nfi' >> ~/.bash_profile
exec "$SHELL"
pyenv shell 3.6.4
pyenv virtualenv env
pip install -r requirements.txt
```

## Development hierarchy 

* Main file: `qsp_network_audit.py`

* Target environments are defined in `config.yaml`

* QSPAuditNode gets params from YAML
  - `config.py`
  - `audit.py`
    - main loop is in the run() method
    - logic for audit computation
    - report is JSON and posted to the private blockchain
  - `analyzer.py`
    - abstracts an analyzer tool
    - needs to accept parameters in a better way
  - security constraints
    - network audit service might have a threat of price forgery (must check)
    - need to control the state of this service
      - uptime monitoring
      - metrics
