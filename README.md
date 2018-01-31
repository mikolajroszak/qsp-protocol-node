# qsp-network-audit
Implements the QSP audit node in the Quantstamp network

## Development

```
brew install pyenv
brew install pyenv-virtualenv
pyenv install 3.6.4
pyenv shell 3.6.4
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"\nfi' >> ~/.bash_profile
exec "$SHELL"
pyenv virtualenv env
pip install -r requirements.txt
```
