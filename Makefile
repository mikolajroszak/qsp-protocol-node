ENV ?= local
CONFIG ?= config.yaml

run:
	python3 qsp_network_audit/qsp_network_audit.py $(ENV) $(CONFIG)

test:
	find tests | egrep "^.*/test_.*.py$$" | xargs python -m unittest

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf
