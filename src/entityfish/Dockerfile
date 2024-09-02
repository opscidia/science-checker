FROM grobid/entity-fishing:0.0.6
LABEL maintainer "loic.rakotoson@opscidia.com"

RUN apt-get update; \
    apt-get install -y \
        curl

# TODO: see of models should be downloaded here or in makefile as volume data
# https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-kb.zip in /opt/entity-fishing/data/db/db-kb
# https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-en.zip in /opt/entity-fishing/data/db/db-en
