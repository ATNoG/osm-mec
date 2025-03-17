FROM python:3.10-alpine

# Install kubectl
RUN apk add --no-cache gcc curl musl-dev linux-headers librdkafka-dev bash

RUN apk add --no-cache --virtual .make-deps bash make patch wget git gcc g++ && apk add --no-cache musl-dev zlib-dev openssl zstd-dev pkgconfig libc-dev libmagic
RUN wget https://github.com/edenhill/librdkafka/archive/v2.8.0.tar.gz
RUN tar -xvf v2.8.0.tar.gz && cd librdkafka-2.8.0 && ./configure --prefix /usr && make && make install

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin

# Upgrade pip
RUN pip install --upgrade pip

# Install osmclient
RUN git clone https://osm.etsi.org/gerrit/osm/osmclient
RUN python3 -m pip install --user /osmclient -r /osmclient/requirements.txt -r /osmclient/requirements-dev.txt

# Copy app files
COPY . /app
WORKDIR /app

# Install app requirements
RUN pip install -r /app/requirements.txt

# Run app
CMD ["python3", "-u", "main.py"]
