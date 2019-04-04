####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.                                                    #
#                                                                                                  #
####################################################################################################

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

RUN apk add --no-cache python3-dev gcc musl-dev libtool automake autoconf
RUN apk add --no-cache libressl-dev make
RUN apk add --no-cache jq
RUN apk add --no-cache libffi-dev
RUN apk add --no-cache linux-headers
RUN apk add --no-cache vim

# Install aws-cli
RUN pip3 install -U awscli

# Install solc
RUN wget https://github.com/ethereum/solidity/releases/download/v0.4.25/solc-static-linux && \
  chmod +x solc-static-linux && \
  mv solc-static-linux /usr/local/bin/solc

RUN mkdir ./app
WORKDIR ./app/
RUN mkdir ./audit-db
COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY .coveragerc .
COPY ./bin ./bin
COPY ./tests/ ./tests/
COPY ./src/ ./src/
COPY ./plugins/ ./plugins/
RUN chmod +x ./bin/qsp-protocol-node
RUN chmod +x ./bin/codec
RUN mkdir -p /var/log/qsp-protocol/
RUN find "./plugins/analyzers/wrappers" -type f -exec chmod +x {} \;
RUN find "./tests/resources/wrappers" -type f -exec chmod +x {} \;
CMD [ "./bin/qsp-protocol-node" ]
