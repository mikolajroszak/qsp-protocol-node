#!/bin/bash


touch $PWD/event_database.db

docker load --input app.tar && \
docker run -it \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v /tmp:/tmp:Z \
	-v $PWD/keystore:/app/keystore:Z \
	-v $PWD/config.yaml:/app/config.yaml:Z \
	-v $PWD/event_database.db:/app/.audit_node.db:Z \
	-e ENV="testnet" \
	-e CONFIG="config.yaml" \
	-e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
	-e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
	-e AWS_DEFAULT_REGION="us-east-1" \
	-e ETH_PASSPHRASE="$ETH_PASSPHRASE" \
	-e ETH_AUTH_TOKEN="$ETH_AUTH_TOKEN" \
	qsp-protocol-node sh -c "make run-with-auto-restart"
