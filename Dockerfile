FROM docker:dind
# for "Docker-in-Docker" support
 
# the following steps are based on https://hub.docker.com/r/frolvlad/alpine-python3/
RUN apk add --no-cache python3 && \
  python3 -m ensurepip && \
  rm -r /usr/lib/python*/ensurepip && \
  pip3 install --upgrade pip setuptools && \
  if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
  if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
  rm -r /root/.cache

RUN pip install -U pkg-config

RUN apk add --no-cache python3-dev gcc musl-dev libtool automake autoconf
RUN apk add --no-cache openssl-dev make
RUN apk add --no-cache libffi-dev
RUN apk add --no-cache linux-headers

# Install aws-cli
RUN pip install -U awscli

# Install solc
RUN wget https://github.com/ethereum/solidity/releases/download/v0.4.21/solc-static-linux && \
  chmod +x solc-static-linux && \
  mv solc-static-linux /usr/local/bin/solc

RUN mkdir ./app
WORKDIR ./app
RUN mkdir ./audit-db
COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install web3[tester]

COPY . .

RUN find "./analyzers" -type f -iname "*.sh" -exec chmod +x {} \;

CMD [ "make", "run" ]
