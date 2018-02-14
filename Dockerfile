FROM 466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-network-audit-base:latest

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
CMD [ "make", "run" ]
