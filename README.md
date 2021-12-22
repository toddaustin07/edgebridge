# Forwarding Bridge Server for SmartThings Edge drivers
## Description
The forwarding bridge server (subsequently referred to as 'server') is designed as a companion to SmartThings Edge drivers that (1) need to send HTTP requests to destinations outside of the LAN, and (2) need to be able to receive extemperaneous HTTP messages issued by LAN-based devices and applications.

The server itself is simply a Python script that can be run on any 'always on' Windows/Linux/Mac/Raspberry Pi computer.  The server is provided either as a 3.7x Python source script or a Windows executable program file.  It can read an optional configuration file created by the user (see below).

The server includes these capabilities:
### 1. Forward HTTP requests from an Edge driver to any URL
A limitation of Edge drivers is that the hub platform allows them to communicate to only **local** IP addresses.  This excludes any internet requests or other external RESTful API calls, for example.  With this solution, an Edge driver can send a request to the server to be forwarded outside the LAN, which the server will do and return the response back to the requesting Edge driver.  (My Web Requestor https://github.com/toddaustin07/webrequestor devices can also be used to initiate these requests)
#### SmartThings API calls
An additional feature of the server is that it recognizes requests being forwarded to the **SmartThings RESTful API**, and using the Bearer Token configured by the user, can forward those requests and return the response, allowing Edge drivers access to any SmartThings API call.  For example, this can allow a driver to get the device status of ANY SmartThings device, and use it in its logic - allowing it to perform SmartApp-like functions.
### 2. Forward messages from LAN-based devices or applications TO a specific Edge driver
Edge drivers cannot use any specific port, so this makes it difficult for other LAN-based configurable devices or applications to be able to send messages directly *TO* an Edge driver without first establishing a unique peer-to-peer or client/server link initiated by the Edge driver.  This is possible, but requires more custom coding on both ends to make it work (discovery, monitoring connection, managing change, etc.).  

This server offers a simpler solution:  an Edge driver 'registers' with the server what LAN IP address it is interested in getting messages from.  The LAN device or application is then configured to send its messages to the server (which has a fixed IP/port number).  Then when the server receives those messages, it looks up who is registered to receive them, and then forwards them to the appropriate IP/port number.  If/when the Edge driver port number changes, it simply re-registers the new port number with the server.  No configuration change is needed at the LAN device or application.  A static IP address is typically recommended for the physical device or application.
#### Example use cases
1. Shelly Motion Sensor
There is currently no official local integration of Shelly's wifi Motion Sensors with SmartThings. There are cloud integrations available for other Shelly devices, but as of this writing there none that supports their motion sensor product.  These devices can be configured to send an HTTP message to a given IP/Port whenever motion or tampering is detected.  With this solution, the device can be configured to send these messages to the server, which will then forward them to registered Edge drivers.
2. Blue Iris camera
The Blue Iris server allows for configuring actions for a camera whenever it detects motion.  These actions can include a web request.  Today, this is typically directed at a cloud-based SmartApp for SmartThings integration.  But with this solution, the web requests can be directed to the bridge server and forwarded to an Edge driver for 100% local execution.

## Installation

Download the Python script or Windows executable file to a folder on your computer.  You can start it manually or preferrably, configure your computer to auto start the program as a service whenever it reboots 
### Configuration file
If you want to change the default **port number** of the server (8088), you can do so by creating a configuration file which will be read when the server is started.  This config file can also be used to provide your **SmartThings Bearer Token** if you plan to do any SmartThings API calls.
The format of the file is as follows:
```
[config]
Server_Port = nnnnn
SmartThings_Bearer_Token = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
This configuration file is **optional**.

## Run the Server

On Mac or Linux, start the server by this command:
```
python3 edgebridge.py
```
On Windows, start the server by running the downloaded executable:
```
edgebridge
```
A good option is to run this in a window where you can monitor the output messages.  You may want to log them permanently to a file as well.

Note that the server creates and maintains a hidden file ('.registrations') which contains records capturing the Edge driver ID, hub address, and LAN device/application IP address to be monitored.  As driver port numbers change due to restarts, the registrations file may contain old records for a short time, but these will eventually be cleared out after 3 failed attempts to communicate with the 'old' port number(s).

## Forwarding Bridge Server Interface Specification

The server uses a simple RESTful API to accept commands from SmartThings Edge drivers.

For purposes of the examples below, we'll assume the server is located at *192.168.1.140:8088*.

### Forwarding Edge Driver HTTP Requests
Scenario:  The Edge driver wants the server to **forward** an HTTP request to somewhere *outside* the LAN
```
[GET | POST] http://192.168.1.140:8088/api/forward?url=<URL string>
```
*URL string* can be any valid URL including paramaters.  Examples:
- http://www.websitename.com
- https://http-bin.org/post?key1=key1value&key2=key2value
- https://api.smartthings.com/v1/devices/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/components/main/capabilities/switch/status

#### Example forwarding requests
```
POST http://192.168.1.140:8088/api/forward?url=https://http-bin.org/post?key1=key1value&key2=key2value
GET http://192.168.1.140:8088/api/forward?url=https://api.smartthings.com/v1/devices/80e99446-a656-41e2-9db7-3981f7c0e126/components/main/capabilities/switch/status
GET http://192.168.1.140:8088/api/forward?url=https://api.wheretheiss.at/v1/satellites/25544
```

### Forwarding device/app message TO an Edge driver
Senario:  The Edge driver wants to receive web requests from a LAN-based device or application
The Edge driver sends a request to the server to **register** a specific device/app address from which it wants to receive messages
```
POST http://192.168.1.140:8088/api/register?devaddr=<address of device/app to listen to>&hubaddr=<hub IP:port in use by the driver>&edgeid=<Edge device.id>
DELETE http://192.168.1.140:8088/api/register?devaddr=<address of device/app to stop listening to>&hubaddr=<hub IP:port in use by the driver>&edgeid=<Edge device.id>
```
*devaddr* can **optionally** include a port number.  Examples:
- 192.168.1.150
- 192.168.1.140:2345

*hubaddr* **MUST** include the port number:
- 192.168.1.107:31732

*edgeid* must be in the format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx; obtained within Edge driver with 'device.id'

#### Example registration request
```
POST http://192.168.1.140:8088/api/register?devaddr=192.168.1.150&hubaddr=192.168.1.107:31732&edgeid=3894BE52-09E8-4CFD-AD5C-580DE59B6873
```

#### Registrations & Scrubbing
A hidden file '.registrations' is maintained by the server to keep a persistant list of driver registrations.  Occassionally, drivers or devices may get deleted without issuing a delete registration command to the server.  As a result, orphaned registrations can exist.  However the server will periodically scrub these when it repeatedly fails to reach the registered driver.  Applicable scrub messages will be displayed by the server when this occurs and should be considered normal.
