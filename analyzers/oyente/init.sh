#!/bin/bash

$(aws ecr get-login --no-include-email --region us-east-1) # this won't be necessary once we switch to public images
docker pull 466368306539.dkr.ecr.us-east-1.amazonaws.com/melonproject-oyente:57dcfae35773ff30aa34856865a7ad07c501d4d0
