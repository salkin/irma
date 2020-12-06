FROM alpine:3.11.5
MAINTAINER niklas.wik@iki.fi

RUN apk add python3 mariadb-client ca-certificates --no-cache && \
    python3 -m ensurepip  && \
    pip3 install --upgrade pip
RUN pip3 install flask requests bs4 schedule waitress mysql-connector
COPY *.py /opt/
COPY src /opt/src
COPY templates /opt/templates


WORKDIR /opt/templates
