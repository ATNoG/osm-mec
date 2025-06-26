# syntax=docker/dockerfile:1
FROM python:3.10-alpine

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apk add --no-cache gcc curl musl-dev linux-headers librdkafka-dev bash
RUN apk add --no-cache --virtual .make-deps bash make patch wget git gcc g++

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
CMD ["python", "app.py"]
