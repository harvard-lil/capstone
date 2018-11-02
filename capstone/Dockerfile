FROM python:3.7-stretch
ENV PYTHONUNBUFFERED 1

# pip
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -U pip; pip install -r requirements.txt --src /usr/local/src

# code
ADD . /app/
