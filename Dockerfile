FROM ubuntu:rolling

RUN apt-get update && apt-get install build-essential make python3
RUN mkdir /analyzer
WORKDIR /analyzer

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
CMD [ "make", "run" ]
