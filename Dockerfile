FROM python:3.6.4

RUN mkdir /myapp
WORKDIR /myapp

COPY . .
CMD [ "python", "hello.py" ]
