# profile_simulated_hardware
Simulated hardware for TES fly scans

## Set up instructions

Install a VirtualBox machine with Sirepo using vagrant following the instructions from 
https://github.com/radiasoft/sirepo/wiki/Development, which is also needed if
https://github.com/NSLS-II/sirepo-bluesky is used.

Configure the ports mapping:
- for the EPICS IOC, port 5064 for the UDP and TCP protocols (the IOC comes with a Docker image ``mikehart/motorsim``,
  or ``europeanspallationsource/motorsim``, based on
  https://github.com/EuropeanSpallationSource/MCAG_setupMotionDemo)
- for MongoDB, port 27017 (needed for databroker)


Install a MongoDB following the instructions from
https://docs.mongodb.com/manual/tutorial/install-mongodb-on-red-hat.


Install Docker following the instructions from
https://docs.docker.com/install/linux/docker-ce/fedora/.



```bash
docker run -it --rm --name motorsim --network=host mikehart/motorsim
```

