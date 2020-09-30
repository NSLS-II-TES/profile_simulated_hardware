#!/bin/bash

export USE_CAPROTO_IOC=

docker run -dt --rm --name motorsim --network=host -e "PREFIX=IOC" europeanspallationsource/motorsim

sleep 10

docker images
docker ps -a

caget IOC:m2
