#!/bin/bash

$(aws ecr get-login --no-include-email --region us-east-1) # this won't be necessary once we switch to public images
docker pull 466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-analyzer-oyente:dev
