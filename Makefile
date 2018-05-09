ENV ?= local
CONFIG ?= config.yaml
ETH_PASSPHRASE ?= ""

# If running locally, outside a container, explicitly 
# set the path where do find the custom version of solc
ifeq ($(ENV), "local")
	 export SOLC_CUSTOM_PATH="./oyente/solc"
endif

# If running outside a container, assume the variable is configured
# properly.

run: # printing "date" is important so Cloud Watch can distinguish log files 
  # the workaround should be removed when switched to Kubernetes
	date; python  -W ignore::DeprecationWarning qsp_protocol_node/qsp_protocol_node.py -v -p $(ETH_PASSPHRASE) $(ENV) $(CONFIG)

test:
	PYTHONPATH=./tests:./qsp_protocol_node pytest --cov=qsp_protocol_node -s --disable-pytest-warnings --cov-report term-missing --cov-report html tests/

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf
