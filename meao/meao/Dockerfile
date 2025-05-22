# syntax=docker/dockerfile:1
FROM python:3.10-alpine

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install kubectl
RUN apk add --no-cache gcc curl musl-dev linux-headers librdkafka-dev bash

RUN apk add --no-cache --virtual .make-deps bash make patch wget git gcc g++ && apk add --no-cache musl-dev zlib-dev openssl zstd-dev pkgconfig libc-dev libmagic
RUN wget https://github.com/edenhill/librdkafka/archive/v2.8.0.tar.gz
RUN tar -xvf v2.8.0.tar.gz && cd librdkafka-2.8.0 && ./configure --prefix /usr && make && make install

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin

# install osmclient
COPY osmclient-install.sh osmclient-install.sh
RUN sh osmclient-install.sh

# set work directory
WORKDIR /app

# install dependencies
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app

# run the application
CMD ["python", "main.py"]
