ENV ?= local
CONFIG ?= config.yaml
ETH_PASSPHRASE ?= ""

# If running outside a container, assume the variable is configured
# properly.

run: # printing "date" is important so Cloud Watch can distinguish log files 
  # the workaround should be removed when switched to Kubernetes
	date; python  -W ignore::DeprecationWarning qsp_protocol_node/qsp_protocol_node.py -p $(ETH_PASSPHRASE) $(ENV) $(CONFIG)

test:
	./analyzers/init.sh && PYTHONPATH=./tests:./qsp_protocol_node pytest --cov=qsp_protocol_node -s -v --disable-pytest-warnings --cov-report term-missing --cov-report html tests/

clean:
	find . | egrep "^.*/(__pycache__|.*\.pyc)$$" | xargs rm -rf

run-docker:
	make clean && docker build -t qsp-protocol-node . && docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-e AWS_ACCESS_KEY_ID="$(shell aws --profile default configure get aws_access_key_id)" \
		-e AWS_SECRET_ACCESS_KEY="$(shell aws --profile default configure get aws_secret_access_key)" \
		-e ETH_PASSPHRASE=$(ETH_PASSPHRASE) \
		qsp-protocol-node sh -c "make run"

test-docker:
	make clean && docker build -t qsp-protocol-node . && docker run -it \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /tmp:/tmp \
		-e AWS_ACCESS_KEY_ID="$(shell aws --profile default configure get aws_access_key_id)" \
		-e AWS_SECRET_ACCESS_KEY="$(shell aws --profile default configure get aws_secret_access_key)" \
		qsp-protocol-node sh -c "make test"
