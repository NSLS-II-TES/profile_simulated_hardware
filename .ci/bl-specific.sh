#!/bin/bash

caget_exists=$(which caget || echo "")

if [ -z "${caget_exists}" ]; then
    echo "caget does not exist. Trying to install it..."
    conda install -p $HOME/miniconda/envs/${CONDA_ENV_NAME} -c nsls2forge -y epics-base
fi

export USE_EPICS_IOC=1

echo -e "env inside $0"
echo -e "========================================================"
env | sort -u
echo -e "========================================================"

if [ ! -z "${USE_EPICS_IOC}" -a "${USE_EPICS_IOC}" -ne 0 ]; then
    docker run -dt --rm --name motorsim --network=host -e "PREFIX=IOC" europeanspallationsource/motorsim

    sleep 10

    docker images
    docker ps -a

    caget IOC:m2
else
    echo "Falling back to use caproto-spoof-beamline IOC"
fi

