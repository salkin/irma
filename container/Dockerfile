FROM alpine:3.10.2
MAINTAINER niklas.wik@iki.fi

RUN apk add python3 --no-cache && \
    python3 -m ensurepip 
RUN pip3 install flask requests bs4 schedule
COPY *.py /opt/
COPY templates /opt/templates

WORKDIR /opt/templates
