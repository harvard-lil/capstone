FROM python:3.5-stretch
ENV PYTHONUNBUFFERED 1

# Get build dependencies and packages required by the app
# pytest-redis requires a local redis instance)
# https://github.com/ClearcodeHQ/pytest-redis/issues/108)
RUN apt-get update \
    && apt-get install -y redis-server

# pip
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install -U pip \
    && pip install -r requirements.txt --src /usr/local/src \
    && rm requirements.txt

# nodejs
RUN curl -sL https://deb.nodesource.com/setup_11.x | bash -
COPY package.json /app
COPY package-lock.json /app
RUN apt-get update \
    && apt-get install -y nodejs \
    && npm install \
    && rm package.json \
    && rm package-lock.json
