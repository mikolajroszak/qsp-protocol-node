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

`qsp_network_audit.py`
  target environment is defined in config.yml
    QSPAuditNode gets params from YAML
    config.py
    audit.py
      everything is in the run() method
      some logic for distributed audit computation
      report is JSON and posted to the private blockchain
    analyzer.py
      abstracts an analyzer tool
      need to accept parameters in a better way
  security constraints
    network audit service has a threat of price forgery
    need to control the state of this service
      uptime monitoring
      metrics
