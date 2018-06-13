ENV ?= local
CONFIG ?= config.yaml
ETH_PASSPHRASE ?= ""

# NOTE: if running outside a container, assume all required environment variables are configured properly.

setup:
	brew install automake libtool awscli pyenv pyenv-virtualenv ; \
	brew install https://raw.githubusercontent.com/ethereum/homebrew-ethereum/9c1da746bbfc9e60831d37d01436a41f4464f0e1/solidity.rb ; \
	rm -rf $(HOME)/.pyenv ; \
	ln -s -f $(shell git rev-parse --show-toplevel)/pre-commit $(shell git rev-parse --show-toplevel)/.git/hooks/pre-commit ; \
	chmod +x $(shell git rev-parse --show-toplevel)/.git/hooks/pre-commit ; \
	pyenv install 3.6.4 ; \
	echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"\nfi' >> ~/.bash_profile ; \
	pyenv virtualenv env ; \
	pip install -r requirements.txt

run: # printing "date" is important due to the logic CloudWatch uses to distinguish log files
	date; python  -W ignore::DeprecationWarning qsp_protocol_node/qsp_protocol_node.py -p $(ETH_PASSPHRASE) $(ENV) $(CONFIG)

test:
	pip install web3[tester] ; \
	./analyzers/init.sh && PYTHONPATH=./tests:./qsp_protocol_node pytest --cov=qsp_protocol_node -s -v --disable-pytest-warnings --cov-report term-missing --cov-report html tests/

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf

run-docker:
	make clean && docker build -t qsp-protocol-node . && docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-e AWS_ACCESS_KEY_ID="$(shell aws --profile default configure get aws_access_key_id)" \
		-e AWS_SECRET_ACCESS_KEY="$(shell aws --profile default configure get aws_secret_access_key)" \
		-e AWS_DEFAULT_REGION="us-east-1" \
		-e ETH_PASSPHRASE=$(ETH_PASSPHRASE) \
		qsp-protocol-node sh -c "make run"

test-docker:
	make clean && docker build -t qsp-protocol-node . && docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-e AWS_ACCESS_KEY_ID="$(shell aws --profile default configure get aws_access_key_id)" \
		-e AWS_SECRET_ACCESS_KEY="$(shell aws --profile default configure get aws_secret_access_key)" \
		-e AWS_DEFAULT_REGION="us-east-1" \
		qsp-protocol-node sh -c "make test"
