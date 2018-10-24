#!/bin/bash

####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.                                                    #
#                                                                                                  #
####################################################################################################

# Find all running qsp-protocol-nodes
if [[ $(docker ps -q --filter ancestor=qsp-protocol-node) ]]; then
    #Attach to the running container and stop the audit process.
    for container in $(docker ps -q --filter ancestor=qsp-protocol-node); do
        docker exec -it $container bash -c 'PID=$(ps auxw | grep "python -W"| grep -v bin| grep -v grep| awk "{print \$1}") ;echo $PID ; kill $PID'
        #Wait for the audit node to stop
        while [[ $(docker inspect --format={{.State.Status}} $container) == "running" ]]; do
            echo "Waiting for Audit node to stop" | tee -a  qsp-protocol-node.log
            sleep 4
        done
        
        echo "Audit node stopped" | tee -a qsp-protocol-node.log
        # Stop run.sh if run in foreground
        kill `ps -A | grep  ./run.sh | grep -v grep | awk '{print $1}'`
done
fi