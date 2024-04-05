FROM python:3.11.9-bookworm
ENV PYTHONUNBUFFERED 1

# Enable apt-get -t buster-backports
#RUN echo 'deb http://deb.debian.org/debian buster-backports main' > /etc/apt/sources.list.d/backports.list

# Get build dependencies and packages required by the app
# FIRST LINE:
# redis-server for pytest-redis (https://github.com/ClearcodeHQ/pytest-redis/issues/108)
# postgresql-client for manage.py dbshell
# libtiff-tools and pdftk for make_pdf.py (tiff2pdf, tiffcp, pdftk commands)
# SECOND LINE:
# librocksdb5.17 et al. for python-rocksdb
# THIRD LINE:
# extra requirements for the yarn puppeteer package, as discovered by running
#  ldd /node_modules/puppeteer/.local-chromium/linux-672088/chrome-linux/chrome | grep not
# and then looking for relevant packages listed in
#  https://github.com/GoogleChrome/puppeteer/blob/master/docs/troubleshooting.md#chrome-headless-doesnt-launch-on-unix
# FOURTH LINE:
# libhyperscan-dev for pip hyperscan package
# FIFTH LINE:
# htmltidy for fastcase ingest
RUN apt-get update \
    && apt-get install -y redis-server postgresql-client libtiff-tools pdftk \
    && apt-get install -y librocksdb7.8 librocksdb-dev libsnappy-dev zlib1g-dev libbz2-dev libgflags-dev liblz4-dev rocksdb-tools \
    && apt-get install -y libx11-xcb1 libxtst6 libgtk-3-0 libnss3 \
    && echo libhyperscan5 libhyperscan/cpu-ssse3 boolean true | debconf-set-selections && apt-get install -y libhyperscan-dev \
    && apt-get install -y tidy \
    && apt-get install -y libdrm2 libgbm-dev \
    && apt-get install --no-install-recommends libdbus-glib-1-2

# pip
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install pip==24.0 \
    && pip install -r requirements.txt --src /usr/local/src \
    && rm requirements.txt

# nodejs
# write a .yarnrc that will only be found inside the docker guest, and will cause
# node_modules to be written to /node_modules instead of ./node_modules:
RUN echo "--modules-folder /node_modules" > /.yarnrc
COPY package.json /app
COPY yarn.lock /app
# pin node version -- see https://github.com/nodesource/distributions/issues/33
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -  \
    && apt-get install -y nodejs=20.12.0-1nodesource1 \
    && npm install -g yarn@1.22.5 \
    && yarn install --frozen-lockfile \
    && rm package.json \
    && rm yarn.lock

# Install Playwright browsers for integration tests
RUN playwright install chromium firefox
