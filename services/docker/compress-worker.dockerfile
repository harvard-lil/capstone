FROM python:3.6-stretch
ENV PYTHONUNBUFFERED 1

# TODO: should use cache-busting by calling apt-get update in every install call

RUN apt-get update && apt-get -y upgrade

# ImageMagick 6
RUN apt-get -y install imagemagick libjpeg-dev

## ImageMagick 7
#RUN apt-get -y install libopenjp2-7
#ADD https://www.imagemagick.org/download/ImageMagick-7.0.7-9.tar.gz /root/build/
#WORKDIR /root/build
#RUN tar xvzf ImageMagick-7.0.7-9.tar.gz
#WORKDIR /root/build/ImageMagick-7.0.7-9
#RUN ./configure && make && make install
## make sure new imagemagick libs are found -- not sure if necessary
#RUN /sbin/ldconfig /usr/local/lib/

# mozjpeg
# not packaged in Debian
# via https://github.com/magnetikonline/dockermozjpegdeb/blob/master/Dockerfile
RUN apt-get -y install autoconf automake libtool nasm make pkg-config libpng-dev
ADD https://github.com/mozilla/mozjpeg/archive/v3.3.1.tar.gz /root/build/
WORKDIR /root/build
RUN tar -xf v3.3.1.tar.gz
WORKDIR /root/build/mozjpeg-3.3.1
RUN autoreconf -fiv
RUN ./configure && make && make install
RUN ln /opt/mozjpeg/bin/cjpeg /usr/local/bin/mozcjpeg

# openjp2
# install 2.3.0 manually to get multithreading
#RUN apt-get -y install libopenjp2-tools
ADD https://github.com/uclouvain/openjpeg/releases/download/v2.3.0/openjpeg-v2.3.0-linux-x86_64.tar.gz /root/build
WORKDIR /root/build
RUN tar -xf openjpeg-v2.3.0-linux-x86_64.tar.gz
WORKDIR /root/build/openjpeg-v2.3.0-linux-x86_64
RUN cp -r bin/* /usr/local/bin/ && cp -r lib/* /usr/local/lib/ && cp -r include/* /usr/local/include/

# optipng
RUN apt-get -y install optipng

# use python3 by default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2

# pip
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -U pip; pip install -r requirements.txt --src /usr/local/src

# cleanup
RUN /sbin/ldconfig /usr/local/lib/
RUN apt-get clean
