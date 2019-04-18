####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.                                                    #
#                                                                                                  #
####################################################################################################

MAKEFLAGS += --silent

QSP_ENV ?= "testnet"
QSP_ENV_CI ?= "dev"
QSP_CONFIG ?= "./resources/config.yaml"
QSP_ETH_PASSPHRASE ?= "abc123ropsten"
QSP_ETH_AUTH_TOKEN ?= "PLEASE-SET-THE-TOKEN"
QSP_IGNORE_CODES=E121,E122,E123,E124,E125,E126,E127,E128,E129,E131,E501
QSP_LOG_DIR ?= $(HOME)/qsp-protocol
AWS_ACCESS_KEY_ID ?= ""
AWS_SECRET_ACCESS_KEY ?= ""
AWS_DEFAULT_REGION ?= ""

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc|tests/coverage/htmlcov|tests/coverage/.coverage|app.tar|.*\.bak)$$" | xargs rm -rf
	rm -f CONTRIBUTE.md
	rm -rf deployment/local/dist
	docker images --format "{{.Repository}}:{{.ID}}" | egrep qspprotocol | cut -d ':' -f2 | xargs docker rmi --force

run: build
	docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(PWD)/resources/keystore:/app/resources/keystore:Z \
		-v $(PWD)/resources/contracts:/app/resources/contracts:Z \
		-v $(PWD)/resources/config.yaml:/app/resources/config.yaml:Z \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_DEFAULT_REGION="$(AWS_DEFAULT_REGION)" \
		-e QSP_ETH_AUTH_TOKEN=$(QSP_ETH_AUTH_TOKEN) \
		-e QSP_ETH_PASSPHRASE="$(QSP_ETH_PASSPHRASE)" \
		qsp-protocol-node sh -c "./bin/qsp-protocol-node -a $(QSP_ENV) $(QSP_CONFIG)"
		
docs:
	markdown-pp CONTRIBUTE.md.template -o ./CONTRIBUTE.md

build:
		docker build -t qsp-protocol-node .

test: build
	docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		qsp-protocol-node sh -c "./bin/qsp-protocol-node -t local"

interactive: build
	docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(PWD)/resources/keystore:/app/resources/keystore:Z \
		-v $(PWD)/resources/contracts:/app/resources/contracts:Z \
		-v $(PWD)/resources/config.yaml:/app/resources/config.yaml:Z \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_DEFAULT_REGION="$(AWS_DEFAULT_REGION)" \
		-e QSP_ETH_AUTH_TOKEN=$(QSP_ETH_AUTH_TOKEN) \
		-e QSP_ETH_PASSPHRASE="$(QSP_ETH_PASSPHRASE)" \
		-e QSP_ENV="dev" \
        -e QSP_CONFIG="$(QSP_CONFIG)" \
        qsp-protocol-node sh

test-travis-ci: build
	docker run -t \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-v $(PWD)/tests/coverage:/app/tests/coverage \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_DEFAULT_REGION="$(AWS_DEFAULT_REGION)" \
		-e QSP_ENV="$(QSP_ENV_CI)" \
		qsp-protocol-node sh -c "./bin/qsp-protocol-node -t ci"

bundle:	
	./bin/create-bundle

check-contract-versions:
	./bin/check-contract-versions
	
stylecheck:
	echo "Running Stylecheck"
	find . -name \*.py -exec flake8 --ignore=$(QSP_IGNORE_CODES) {} +
	find . -name \*.py -exec pycodestyle --ignore=$(QSP_IGNORE_CODES) {} +
	echo "Stylecheck passed"

elk:
	cd deployment/local/elk && docker-compose up -d
