FROM ubuntu:rolling

RUN apt-get update && apt-get install -y build-essential make python3 python3-pip pkg-config golang-go libssl-dev zlib1g-dev libffi-dev autoconf libtool wget
RUN mkdir /analyzer
WORKDIR /analyzer

COPY requirements.txt ./
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.6 2
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 2

RUN wget https://gethstore.blob.core.windows.net/builds/geth-alltools-linux-amd64-1.6.6-10a45cb5.tar.gz && \
	tar -xvf geth-alltools-linux-amd64-1.6.6-10a45cb5.tar.gz && mv geth-alltools-linux-amd64-1.6.6-10a45cb5/* /usr/local/bin/

RUN wget https://github.com/ethereum/solidity/releases/download/v0.4.18/solc-static-linux && \
	chmod +x solc-static-linux && mv solc-static-linux /usr/local/bin/solc

RUN pip install -r requirements.txt

COPY . .
CMD [ "make", "run" ]
