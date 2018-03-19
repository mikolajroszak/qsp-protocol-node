ENV ?= local
CONFIG ?= config.yaml
QSP_PASSWORD ?= ""
ifeq ($(ENV), "local")
	 export SOLC_CUSTOM_PATH="./oyente/solc"
else
	 export SOLC_CUSTOM_PATH="/oyente/solc"
endif

#@echo $(SOLC_CUSTOM_PATH)

run: # printing "date" is important so Cloud Watch can distinguish log files 
  # the workaround should be removed when switched to Kubernetes
	date; python  -W ignore::DeprecationWarning qsp_network_audit/qsp_network_audit.py -v -p $(QSP_PASSWORD) $(ENV) $(CONFIG)

test:
	find tests | egrep "^.*/test_.*.py$$" | xargs python -m unittest

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf
