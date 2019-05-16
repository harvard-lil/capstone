FROM python:3.5-stretch
ENV PYTHONUNBUFFERED 1

# Get build dependencies and packages required by the app
# pytest-redis requires a local redis instance)
# https://github.com/ClearcodeHQ/pytest-redis/issues/108)
# psql for manage.py dbshell
RUN apt-get update \
    && apt-get install -y redis-server postgresql-client

# pip
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install -U pip \
    && pip install -r requirements.txt --src /usr/local/src \
    && rm requirements.txt

# nodejs
RUN curl -sL https://deb.nodesource.com/setup_11.x | bash -
# write a .yarnrc that will only be found inside the docker guest, and will cause
# node_modules to be written to /node_modules instead of ./node_modules:
RUN echo "--modules-folder /node_modules" > /.yarnrc
COPY package.json /app
COPY yarn.lock /app
RUN apt-get update \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    && yarn install --frozen-lockfile \
    && rm package.json \
    && rm yarn.lock
