#!/bin/bash
cp "$1" /tmp/
# On Mac, by default, only a few locations can be used for mounting
# Copy the file to /tmp/ and then extract the output from there
basename=$(basename "$1")
docker run -v /tmp/:/shared/ -i 466368306539.dkr.ecr.us-east-1.amazonaws.com/melonproject-oyente:57dcfae35773ff30aa34856865a7ad07c501d4d0 bash -c "python /oyente/oyente/oyente.py -j -s /shared/$basename"
cp "/tmp/$basename.json" "$1.json"
