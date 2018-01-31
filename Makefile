ENV ?= local
CONFIG ?= config.yaml

run:
	python qsp_network_audit/qsp_network_audit.py -v $(ENV) $(CONFIG)

test:
	find tests | egrep "^.*/test_.*.py$$" | xargs python -m unittest

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf
