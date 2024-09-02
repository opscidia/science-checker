FROM python:3.11.9-slim-bullseye
LABEL maintainer "loic.rakotoson@opscidia.com"

WORKDIR /usr/src/back
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update; \
    apt-get install -y \
    gcc \
    build-essential \
    libpq-dev \
    netcat-traditional \
    curl \
    git

COPY ./requirements.txt ./install_requirements.txt
RUN pip3 install nltk
RUN python -m nltk.downloader wordnet omw-1.4
RUN python -m pip install -r install_requirements.txt