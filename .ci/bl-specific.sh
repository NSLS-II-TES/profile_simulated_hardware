#!/bin/bash

export USE_EPICS_IOC=1

docker run -dt --rm --name motorsim --network=host -e "PREFIX=IOC" europeanspallationsource/motorsim

sleep 10

docker images
docker ps -a

caget IOC:m2
