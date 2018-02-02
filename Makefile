ENV ?= local
CONFIG ?= config.yaml
QSP_PASSWD ?= ""

run:
	python qsp_network_audit/qsp_network_audit.py -p $(QSP_PASSWD) $(ENV) $(CONFIG)

test:
	find tests | egrep "^.*/test_.*.py$$" | xargs python -m unittest

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf
