# EdgeBridge Docker-Compose Support

## Overview

Integration with Docker was created to enable simple support for long-term running of the python server.

The provided `Dockerfile` builds a Python 3 image, copies the python script, edgebridge configuration file and requirements.txt to run the service.

In our example we are deploying using docker-compose to a specific docker network, that runs in a specific 'smarthome' CIDR block.

For building and analyzing responses with the Smartthings API, we recommend using the `jq` package - https://stedolan.github.io/jq/

### Configuration

#### Building the Docker Image (optional)

**FIRST COPY THE edgebridge.py and requirements.txt files into the ./docker directory as docker build cannot see parent folders**

To build the docker image, update the `edgebridge.cfg` file first, replacing the "" with your Smartthings Bearer Token obtained from the instructions in the EdgeBridge root documentation.

Building the image is not required with the provided example docker-config file, which already contains a build command

```
[config]
Server_Port = 8088
SmartThings_Bearer_Token = ""
```

Build the image:

```
docker build .
```

##### Docker-Compose

**FIRST COPY THE edgebridge.py and requirements.txt files into the ./docker directory as docker build cannot see parent folders**

To deploy using docker-compose, simply provide the IP Address Subnet for the network you use, the default gateway (router) IP Address, DNS Server (router) and IP Address.

There is a commented out data volume mount example, if you prefer to externalize your configuration file rather than build it.

To start the service:

```sh
docker-compose up -d --build
```

You can test with a simple list command, that will output all of your Smartthings devices in JSON format:

```
curl --request GET "http://10.40.1.18:8088/api/forward?url=https://api.smartthings.com/v1/devices"
```

