# syntax=docker/dockerfile:1
FROM python:3.10-alpine

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apk add --no-cache gcc curl musl-dev linux-headers librdkafka-dev bash
RUN apk add --no-cache --virtual .make-deps bash make patch wget git gcc g++ libmagic

# Install osmclient
RUN git clone https://osm.etsi.org/gitlab/osm/osmclient -b v17.0 /osmclient
RUN python3 -m pip install --no-cache-dir --no-build-isolation --user /osmclient -r /osmclient/requirements.txt -r /osmclient/requirements-dev.txt

# set work directory
WORKDIR /app

# install dependencies
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app

# run the application
CMD ["python", "app.py"]
