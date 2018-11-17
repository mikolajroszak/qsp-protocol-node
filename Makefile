####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.                                                    #
#                                                                                                  #
####################################################################################################

MAKEFLAGS += --silent

QSP_ENV ?= testnet
QSP_CONFIG ?= deployment/local/config.yaml
QSP_ETH_PASSPHRASE ?= abc123ropsten
QSP_ETH_AUTH_TOKEN ?= \"\"
IGNORE_CODES=E121,E122,E123,E124,E125,E126,E127,E128,E129,E131,E501


# NOTE: if running outside a container, assume all required environment variables are configured properly.

# Default target
run: # printing "date" is important due to the logic CloudWatch uses to distinguish log files
	date
	python -W ignore::DeprecationWarning qsp_protocol_node/qsp_protocol_node.py -p "$(QSP_ETH_PASSPHRASE)" -t "$(QSP_ETH_AUTH_TOKEN)" $(QSP_ENV) $(QSP_CONFIG)

run-with-auto-restart:
	./auto-restart

setup:
	pyenv uninstall -f 3.6.4
	ln -s -f $(shell git rev-parse --show-toplevel)/pre-commit $(shell git rev-parse --show-toplevel)/.git/hooks/pre-commit
	chmod +x $(shell git rev-parse --show-toplevel)/.git/hooks/pre-commit
	pyenv install 3.6.4
	pip install -r requirements.txt

test:
	pip install web3[tester]
	PYTHONPATH=./tests:./qsp_protocol_node pytest --cov=qsp_protocol_node -s -v --disable-pytest-warnings --cov-config .coveragerc --cov-report term-missing --cov-report html tests/

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc|tests/coverage/htmlcov|tests/coverage/.coverage|app.tar)$$" | xargs rm -rf

run-docker:
	make clean
	docker build -t qsp-protocol-node .
	docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(PWD)/deployment/local/keystore:/app/keystore:Z \
		-e AWS_ACCESS_KEY_ID="$(shell aws --profile default configure get aws_access_key_id)" \
		-e AWS_SECRET_ACCESS_KEY="$(shell aws --profile default configure get aws_secret_access_key)" \
		-e AWS_DEFAULT_REGION="us-east-1" \
		-e QSP_ETH_PASSPHRASE="$(QSP_ETH_PASSPHRASE)" \
		-e QSP_ETH_AUTH_TOKEN="$(QSP_ETH_AUTH_TOKEN)" \
		qsp-protocol-node sh -c "make run"

test-docker:
	make clean
	docker build -t qsp-protocol-node .
	docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-e AWS_ACCESS_KEY_ID="$(shell aws --profile default configure get aws_access_key_id)" \
		-e AWS_SECRET_ACCESS_KEY="$(shell aws --profile default configure get aws_secret_access_key)" \
		-e AWS_DEFAULT_REGION="us-east-1" \
		qsp-protocol-node sh -c "make test"

test-ci:
	docker build --cache-from $(CACHE_IMAGE) -t qsp-protocol-node .
	docker run -t \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(PWD)/tests/coverage:/app/tests/coverage \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_SESSION_TOKEN="$(AWS_SESSION_TOKEN)" \
		-e AWS_DEFAULT_REGION="us-east-1" \
		-e QSP_ENV="$(QSP_ENV)" \
		qsp-protocol-node sh -c "make test"

bundle:
	./create-bundle.sh

stylecheck:
	echo "Running Stylecheck"
	find . -name \*.py -exec pycodestyle --ignore=$(IGNORE_CODES) {} +
	echo "Stylecheck passed"
