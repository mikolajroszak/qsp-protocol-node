ENV ?= local
CONFIG ?= config.yaml
QSP_PASSWORD ?= ""
run: # printing "date" is important so Cloud Watch can distinguish log files 
  # the workaround should be removed when switched to Kubernetes
	date; python  -W ignore::DeprecationWarning qsp_network_audit/qsp_network_audit.py -v -p $(QSP_PASSWORD) $(ENV) $(CONFIG)

test:
	PYTHONPATH=./tests:./qsp_network_audit pytest --cov=qsp_network_audit -s --disable-pytest-warnings --cov-report term-missing --cov-report html tests/

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf
