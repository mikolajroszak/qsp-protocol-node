ENV ?= testnet
IMAGE ?= 466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-protocol-node:develop
ETH_PASSPHRASE ?= \"abc123ropsten\"
AWS_ACCESS_KEY_ID ?= "$(shell aws --profile default configure get aws_access_key_id)"
AWS_SECRET_ACCESS_KEY ?= "$(shell aws --profile default configure get aws_secret_access_key)"

download:
	$(shell aws ecr get-login --region us-east-1 --no-include-email) && \
	docker pull $(IMAGE)

run:
	docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-v $(PWD)/keystore:/app/keystore \
		-v $(PWD)/config.yaml:/app/config.yaml \
		-e ENV="$(ENV)" \
		-e AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
		-e AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
		-e AWS_DEFAULT_REGION="us-east-1" \
		-e ETH_PASSPHRASE="$(ETH_PASSPHRASE)" \
		qsp-protocol-node sh -c "make run-with-auto-restart"
