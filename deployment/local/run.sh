#!/bin/bash

####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.                                                    #
#                                                                                                  #
####################################################################################################

# Check if the script is running in background
case $(ps -o stat= -p $$) in
  *+*) IN_BACKGROUND="false" ;;
  *) IN_BACKGROUND="true" ;;
esac

bash ./stop.sh

touch $PWD/event_database.db

docker load --input app.tar && \
docker run -d \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v /tmp:/tmp:Z \
	-v $PWD/keystore:/app/keystore:Z \
	-v $PWD/config.yaml:/app/config.yaml:Z \
	-v $PWD/event_database.db:/root/.audit_node.db:Z \
	-e ENV="testnet" \
	-e CONFIG="config.yaml" \
	-e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
	-e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
	-e AWS_DEFAULT_REGION="us-east-1" \
	-e ETH_PASSPHRASE="$ETH_PASSPHRASE" \
	-e ETH_AUTH_TOKEN="$ETH_AUTH_TOKEN" \
	qsp-protocol-node sh -c "make run-with-auto-restart"


# Redirect log for the docker to a log file in current directory 
docker logs --follow $(docker ps -a -q --latest --filter "status=running" --filter ancestor=qsp-protocol-node) > qsp-protocol-node.log &

# Tail the logs if not in background
if [ "$IN_BACKGROUND" == "false" ]; then
	while [ ! -f ./qsp-protocol-node.log ]
	do
  		sleep 1
	done
	echo "Displaying logs from qsp-protocol-node.log file..."
	tail -f -n +1 qsp-protocol-node.log
fi
