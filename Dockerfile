FROM python:3.6.5

RUN mkdir ./app
WORKDIR ./app
RUN mkdir ./audit-db
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
CMD [ "make", "run" ]
