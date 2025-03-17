# syntax=docker/dockerfile:1
FROM python:3.10

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
