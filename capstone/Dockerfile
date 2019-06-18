FROM python:3.5-stretch
ENV PYTHONUNBUFFERED 1

# Get build dependencies and packages required by the app
# redis-server for pytest-redis (https://github.com/ClearcodeHQ/pytest-redis/issues/108)
# postgresql-client for manage.py dbshell
# librocksdb5.17 et al. for python-rocksdb
RUN echo 'deb http://deb.debian.org/debian stretch-backports main' > /etc/apt/sources.list.d/backports.list
RUN apt-get update \
    && apt-get install -y redis-server postgresql-client \
    && apt-get install -t stretch-backports -y librocksdb5.17 libzstd-dev liblz4-dev libgflags-dev libbz2-dev zlib1g-dev libsnappy-dev librocksdb-dev rocksdb-tools

# pip
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install -U pip \
    && pip install -r requirements.txt --src /usr/local/src \
    && rm requirements.txt

# nodejs
# write a .yarnrc that will only be found inside the docker guest, and will cause
# node_modules to be written to /node_modules instead of ./node_modules:
RUN echo "--modules-folder /node_modules" > /.yarnrc
COPY package.json /app
COPY yarn.lock /app
# pin node version -- see https://github.com/nodesource/distributions/issues/33
RUN curl -o nodejs.deb https://deb.nodesource.com/node_11.x/pool/main/n/nodejs/nodejs_11.15.0-1nodesource1_amd64.deb \
    && dpkg -i ./nodejs.deb \
    && rm nodejs.deb \
    && npm install -g yarn@1.16.0 \
    && yarn install --frozen-lockfile \
    && rm package.json \
    && rm yarn.lock
