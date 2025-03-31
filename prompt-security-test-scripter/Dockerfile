FROM python:latest
RUN mkdir /req
ADD requirements.txt /req
WORKDIR /req
RUN pip install -r requirements.txt
WORKDIR /py
