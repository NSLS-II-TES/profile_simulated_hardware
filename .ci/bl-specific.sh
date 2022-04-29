#!/bin/bash

set -vxeuo pipefail

mkdir -v -p $HOME/.config/tiled/profiles/
cat << EOF > $HOME/.config/tiled/profiles/profiles.yml
${BEAMLINE_ACRONYM:-local}:
  direct:
    authentication:
      allow_anonymous_access: true
    trees:
    - tree: databroker.mongo_normalized:Tree.from_uri
      path: /
      args:
        uri: mongodb://localhost:27017/metadatastore-local
        asset_registry_uri: mongodb://localhost:27017/asset-registry-local
EOF

sudo mkdir -v -p /etc/bluesky/
sudo cp -v config/kafka.yml /etc/bluesky/kafka.yml

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

    caproto-get -vvvv IOC:m2
else
    echo "Falling back to use caproto-spoof-beamline IOC"
fi

