#!/bin/bash

mkdir -p ./visualization/checker/app_cache/
mkdir -p ./visualization/logs
chmod -R 777 ./visualization/checker/app_cache/
chmod -R 777 ./visualization/logs

cp env.prod .env

docker-compose -p checker build

docker-compose -p checker up -d