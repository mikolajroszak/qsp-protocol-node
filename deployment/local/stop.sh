#!/bin/bash

####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.                                                    #
#                                                                                                  #
####################################################################################################
source common.sh
isrunning () {
	return `ps -A -o pid | grep -q $1`
 }
# Find all running qsp-protocol-nodes
if [[ $(docker ps -q --filter ancestor=qsp-protocol-node) ]]; then
    #Attach to the running container and stop the audit process.
    for container in $(docker ps -q --filter ancestor=qsp-protocol-node); do
        docker exec -it $container bash -c 'PID=$(ps auxw | grep "python -W"| grep -v bin| grep -v grep| awk "{print \$1}") ;echo $PID ; kill $PID'
        #Wait for the audit node to stop
        while [[ $(docker inspect --format={{.State.Status}} $container) == "running" ]]; do
            echo "Waiting for Audit node to stop" | tee -a  $LOG_PATH
            sleep 4
        done
        
        RPID=`cat /tmp/qsp-protocol.pid`
        if [ `isrunning $RPID` ]; then
	        kill $RPID
        	if [ `isrunning $RPID` ]; then
            		echo "Failed to stop the node" | tee -a $LOG_PATH
        	else
            		echo "Audit node stopped" | tee -a $LOG_PATH
        	fi
	else
		echo "No process running"
	fi
    done
else
    echo "Nothing to stop!"
fi
