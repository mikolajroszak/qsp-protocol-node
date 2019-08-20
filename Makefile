####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

MAKEFLAGS += --silent

QSP_ENV ?= "testnet"
QSP_ENV_CI ?= "dev"
QSP_CONFIG ?= "./resources/config.yaml"
QSP_ETH_PASSPHRASE ?= "abc123ropsten"
QSP_ETH_AUTH_TOKEN ?= "PLEASE-SET-THE-TOKEN"
QSP_HOST_USOLC = $(PWD)/bin/solc
QSP_CONTAINER_USOLC = /opt/usolc/bin/solc
QSP_LOG_DIR ?= "$(HOME)/qsp-protocol"
QSP_DOCKER_SOCKET = "/var/run/docker.sock"
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
		-v $(QSP_DOCKER_SOCKET):$(QSP_DOCKER_SOCKET) \
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
	markdown-pp ./.github/CONTRIBUTE.mdTemplate -o ./CONTRIBUTE.md
	mkdir -p .github/ISSUE_TEMPLATE
	markdown-pp ./.github/bug_report.mdTemplate -o ./.github/ISSUE_TEMPLATE/bug_report.md
	markdown-pp ./.github/pull_request_template.mdTemplate -o ./.github/pull_request_template.md
	curl https://raw.githubusercontent.com/quantstamp/opensource-doc-gen/master/CODE_OF_CONDUCT.md > .github/CODE_OF_CONDUCT.md
	curl https://raw.githubusercontent.com/quantstamp/opensource-doc-gen/master/github_template/feature_request.md > .github/ISSUE_TEMPLATE/feature_request.md

build:
	docker build -t qsp-protocol-node .

# test: build
# 	docker run -it \
# 		-v $(QSP_DOCKER_SOCKET):$(QSP_DOCKER_SOCKET) \
# 		-v /tmp:/tmp \
# 		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
# 		-e $(QSP_DOCKER_SOCKET)="$(QSP_DOCKER_SOCKET)" \
# 		qsp-protocol-node sh -c "./bin/qsp-protocol-node -t local"

test: build
	docker run -it \
		-v /tmp:/tmp \
		-v $(PWD):$(PWD) \
		-v $(QSP_DOCKER_SOCKET):$(QSP_DOCKER_SOCKET) \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-e QSP_HOME="$(PWD)" \
		-e QSP_HOST_USOLC="$(QSP_HOST_USOLC)" \
		-e QSP_CONTAINER_USOLC="$(QSP_CONTAINER_USOLC)" \
		-e QSP_DOCKER_SOCKET="$(QSP_DOCKER_SOCKET)" \
 		qsp-protocol-node sh -c "$(PWD)/bin/qsp-protocol-node -t local"


interactive: build
	docker run -it \
		-v $(QSP_DOCKER_SOCKET):$(QSP_DOCKER_SOCKET) \
		-v /tmp:/tmp \
		-v $(QSP_HOST_USOLC):$(QSP_CONTAINER_USOLC):Z \
		-v $(PWD)/resources/keystore:/app/resources/keystore:Z \
		-v $(PWD)/resources/contracts:/app/resources/contracts:Z \
		-v $(PWD)/resources/config.yaml:/app/resources/config.yaml:Z \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_DEFAULT_REGION="$(AWS_DEFAULT_REGION)" \
		-e QSP_ETH_AUTH_TOKEN=$(QSP_ETH_AUTH_TOKEN) \
		-e QSP_ETH_PASSPHRASE="$(QSP_ETH_PASSPHRASE)" \
		-e QSP_HOME="$(PWD)" \
		-e QSP_ENV="dev" \
        -e QSP_CONFIG="$(QSP_CONFIG)" \
		-e QSP_HOST_USOLC="$(QSP_HOST_USOLC)" \
		-e QSP_CONTAINER_USOLC="$(QSP_CONTAINER_USOLC)" \
		-e QSP_DOCKER_SOCKET="$(QSP_DOCKER_SOCKET)" \
        qsp-protocol-node sh

test-travis-ci: build
	docker run -t \
		-v $(QSP_DOCKER_SOCKET):$(QSP_DOCKER_SOCKET) \
		-v /tmp:/tmp \
		-v $(PWD)/bin/solc:"$(QSP_USOLC_BIN_DIR/solc)":Z \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-v $(PWD)/tests/coverage:/app/tests/coverage \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_DEFAULT_REGION="$(AWS_DEFAULT_REGION)" \
		-e QSP_ENV="$(QSP_ENV_CI)" \
		-e QSP_HOME="$(PWD)" \
		-e QSP_USOLC_BIN_DIR="$(QSP_USOLC_BIN_DIR)" \
		-e QSP_DOCKER_SOCKET="$(QSP_DOCKER_SOCKET)" \
		qsp-protocol-node sh -c "./bin/qsp-protocol-node -t ci"

bundle:	
	./bin/create-bundle

check-contract-versions:
	./bin/check-contract-versions
	
stylecheck: build
	docker run -t \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(QSP_LOG_DIR):/var/log/qsp-protocol:Z \
		-v $(PWD)/tests/coverage:/app/tests/coverage \
		-e QSP_ENV="$(QSP_ENV_CI)" \
		qsp-protocol-node sh -c "./bin/stylecheck"

elk:
	cd deployment/local/elk && docker-compose up -d
