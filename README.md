# Forwarding Bridge Server for SmartThings Edge drivers
## Description
The forwarding bridge server (subsequently referred to as 'server') is designed as a companion to SmartThings Edge drivers that (1) need to send HTTP requests to destinations outside of the LAN, and/or (2) need to be able to receive extemperaneous HTTP messages issued by LAN-based devices and applications.

The server itself is simply a Python script that can be run on any 'always on' Windows/Linux/Mac/Raspberry Pi computer.  The server is provided as a 3.7x Python source script, a Windows executable program file, or a Raspberry Pi OS executable program file.  It can read an optional configuration file created by the user (see below).

### Latest Update
The latest update includes these enhancements:
- standardized logging output with control of console vs file logging
- configurable timeout for forwarded requests
- forwarding of request body data now supported
- Optional SmartThings driver device to monitor edgebridge and notify you if down

### Capabilities
The server includes these capabilities:
#### 1. Forward HTTP requests from an Edge driver to any URL
A limitation of Edge drivers is that the hub platform allows them to communicate to only **local** IP addresses.  This excludes any internet requests or other external RESTful API calls, for example.  With this solution, an Edge driver can send a request to the server to be forwarded outside the LAN, which the server will do and return the response back to the requesting Edge driver.  (My Web Requestor https://github.com/toddaustin07/webrequestor devices can also be used to initiate these requests)

##### SmartThings API calls
An additional feature of the server is that it recognizes requests being forwarded to the **SmartThings RESTful API**, and using the Bearer Token configured by the user, can forward those requests and return the response, allowing Edge drivers access to any SmartThings API call.  For example, this can allow a driver to get the device status of ANY SmartThings device, and use it in its logic - allowing it to perform SmartApp-like functions.
#### 2. Forward messages from LAN-based devices or applications TO a specific Edge driver
Edge drivers cannot use any specific port, so this makes it difficult for other LAN-based configurable devices or applications to be able to send messages directly *TO* an Edge driver without first establishing a unique peer-to-peer or client/server link initiated by the Edge driver.  This is possible, but requires more custom coding on both ends to make it work (discovery, monitoring connection, managing change, etc.).  

This server offers a simpler solution:  an Edge driver 'registers' with the server what LAN IP address it is interested in getting messages from.  The LAN device or application is then configured to send its messages to the server (which has a fixed IP/port number).  Then when the server receives those messages, it looks up who is registered to receive them, and then forwards them to the appropriate port number on the SmartThings hub.  If/when the Edge driver's assigned port number changes, it simply re-registers the new port number with the server.  No configuration change is needed at the LAN device or application.  (A static IP address is typically recommended for the physical device or application.)

#### Example use cases
##### Weather Device
A SmartThings Edge driver to provide weather data uses this bridge server to provide current weather conditions and weather forecasts.  The data is retrieved from various internet weather sources that publish access APIs.

Both of the following two example use cases can be implemented, with this bridge server, using my **Edge driver for LAN-based motion sensors** (https://github.com/toddaustin07/lanmotion).

##### Shelly Motion Sensor
There is currently no official local integration of Shelly's wifi Motion Sensors with SmartThings. There are cloud integrations available for other Shelly devices, but as of this writing there are none that support their motion sensor product.  These devices can be configured to send an HTTP message to a given IP/Port whenever motion or tampering is detected.  With this solution, the device can be configured to send these messages to the server, which will then forward them to registered Edge drivers.
##### Blue Iris camera
The Blue Iris server allows for configuring actions for a camera whenever it detects motion.  These actions can include a web request.  Today, this is typically directed at a cloud-based SmartApp for SmartThings integration.  But with this solution, the web requests can be directed to the bridge server and forwarded to an Edge driver for 100% local execution.  

Note that the forwarding bridge server can be run on the same machine as the Blue Iris server itself.

##### Phone tracking application
Another example of an application that can leverage the bridge server to send messages to an Edge driver is my experimental phone tracker app that is available here-> https://github.com/toddaustin07/phonepresence

This application monitors the presence of a cellphone on the home LAN and reports updates back to a LANPresence Edge driver to provide SmartThings presence devices representing the present/away state of the cellphone(s).

##### Ping tracker application
[This application](https://github.com/toddaustin07/PingTracker) runs on an always-on computer on your LAN and issues ping messages to see if the device at the specified IP is answering.  The results are forwarded to a SmartThings Edge LAN presence driver (available on my [test channel](https://bestow-regional.api.smartthings.com/invite/Q1jP7BqnNNlL)).  

##### LAN Triggers
Any LAN-based device or application that can be configured to send an HTTP request can trigger an Edge button device for invoking SmartThings automation routines and Rules.  This provides a super-simple way of connecting LAN-based things locally to SmartThings without having the burden of coding a complicated communications interface.  This can easily be expanded to other device types beyond buttons (lights, switches, thermostats, etc.)

See the Edge driver available here -> https://github.com/toddaustin07/lantrigger

## Installation

This application comes in three forms:

* edgebridge.py:  Python 3.x script (for any OS platform supporting Python 3)
* edgebridge.exe:  Windows executable (built for Windows 10)
* edgebridge4pi:  Raspberry Pi executable (for OS = Raspbian GNU/Linux 10 (buster), CPU = ARMv7)

If you have a Raspberry Pi with Python 3.x you can run the Python script, but if you don't have Python 3.x, you can use the executable.

Download the Python script or applicable executable file to a folder on your computer.  You can start it manually or preferrably, configure your computer to auto start the program as a service whenever it reboots (see instructions below for doing this on a Raspberry Pi).

### Configuration file (optional, but recommended)
The edgebridge.cfg included in this package provides a template you can use.

The configuration file provides the ability to specify the following:
- port number for the server to use (defaults to 8088 if not specified)
- Your SmartThings Bearer Token if you plan to access the SmartThings RESTful API
- Timeout value, in seconds, for forwarded requests (defaults to 5 seconds)
- Message logging control
  - Turn on/off console and file logging
  - Specify log file name
  
The format of the file is as follows:
```
[config]
Server_Port = 8088
SmartThings_Bearer_Token = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
forwarding_timeout = 5
console_output = yes
logfile_output = no
logfile = edgebridge.log
```

If you plan to run edgebridge as a background task or auto-started at boot-up, it is recommended to disable console output and enable logfile output.  In Linux, the **tail** command can be useful to temporarily monitor the contents of the logfile in realtime:
  ```
  tail -f edgebridge.log
  ```
Logfile output can be disabled when it is no longer needed.  The logfile can potentially grow quite large over time - especially if the -d flag is used (see *Debug-level messages* topic below).

### Docker
Please see the [README file](https://github.com/toddaustin07/edgebridge/blob/main/docker/README.md) in the docker folder for details about running edgebridge in a Docker container.

## Run the Forwarding Bridge Server

On Windows, Mac or Linux with Python 3.x available, start the server by this command:
```
python3 edgebridge.py
```
On Windows, start the server by running the downloaded executable:
```
edgebridge
```
On a Raspberry Pi, before you can run the file you downloaded, you need to change the file permissions so it is executable, using the first command below.  Then you can start the server anytime thereafter using the second command below:
```
chmod +x edgebridge4pi
./edgebridge4pi
```

A good option is to run the bridge server in a window where you can monitor the output messages.  You may want to log them permanently to a file as well.

### Debug-level messages
If you want to enable debug-level messages, start the application with a -d parameter.  For example:
```
python3 edgebridge.py -d
```
This option will enable you to see the data being received back from forwarded requests.

### Auto loading at system boot (Raspberry Pi)

If you want edgebridge to automatically start and run in the background whenever your system boots, follow these steps:

- Create a systemd service file:
  ```
  cd /lib/systemd/system
  sudo nano edgebridge.service
  ```
  
- Create the following file contents
  - Choose the "ExecStart=" line option that loads the edgebridge file you are using (executable or Python script)
  - Substitute \<*mydir*> with whatever subdirectory you have edgebridge and its configuration file in

  ```
  [Unit]
  Description=edgebridge application
  After=network.target

  [Service]
  ExecStart=/home/pi/<mydir>/edgebridge4pi
              -- OR --
  ExecStart=/usr/bin/python3 /home/pi/<mydir>/edgebridge.py
  WorkingDirectory=/home/pi/<mydir>
  Restart=always
  RestartSec=60

  [Install]
  WantedBy=multi-user.target
  ```

*Make sure that your edgebridge.cfg file is in the working directory directory as well.*

- After saving the service file, perform these commands:

  > sudo systemctl daemon-reload

  ^This tells systemd to recognize the new service

  > sudo systemctl enable edgebridge.service

  ^This tells systemd to start the service at boot time

- At any time you can use some of the other systemctl commands, the most useful being:

  * sudo systemctl status edgebridge
  * sudo systemctl stop edgebridge
  * sudo systemctl start edgebridge

You can use the Linux **htop** command to confirm that edgebridge is loaded and running.

## Optional edgebridge server monitoring
A SmartThings driver is available on [this channel](https://bestow-regional.api.smartthings.com/invite/Q1jP7BqnNNlL) that can be used to notify you if edgebridge is not responding for whatever reason.  

Enroll your hub in the channel above and select **EdgeBridge Monitor V1** from the list of drivers to install.  Once the driver is available on your hub, the next time you use the mobile app to perform an *Add device / Scan for nearby devices*, a new device called 'Edgebridge Monitor' will be created in your 'No room assigned' room. Go into device Settings for this new device and configure the Bridge Address and ping frequency in seconds.  

The driver will then proceed to send a short message to the edgebridge server at the interval you specified, and show either 'online' or 'offline' on the device Controls screen.  You can create an automation routine to notify yourself when the status goes to 'offline'

Note that in order to avoid false alarms, if edgebridge does not respond to a ping, the ping will be retried two more times at 5 second intervals before status is changed to 'offline'.

## Forwarding Bridge Server Interface Specification
This section is for Edge driver developers or those configuring [Web Requestor](https://github.com/toddaustin07/webrequestor#readme) URLs that use the Bridge Server.

The server uses a simple RESTful API to accept commands from SmartThings Edge drivers.

For purposes of the examples below, we'll assume the server is located at *192.168.1.140:8088*.

### Forwarding Edge Driver HTTP Requests
Scenario:  The Edge driver wants the server to **forward** an HTTP request to somewhere *outside* the LAN

The Edge driver would issue the following HTTP request to the fowarding bridge server:
```
[GET | POST] http://192.168.1.140:8088/api/forward?url=<URL string>
```
*URL string* can be any valid URL including parameters.  Examples:
- http://www.websitename.com
- https://http-bin.org/post?key1=key1value&key2=key2value
- https://api.smartthings.com/v1/devices/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/components/main/capabilities/switch/status

#### Example forwarding requests
```
POST http://192.168.1.140:8088/api/forward?url=https://http-bin.org/post?key1=key1value&key2=key2value
GET http://192.168.1.140:8088/api/forward?url=https://api.smartthings.com/v1/devices/80e99446-a656-41e2-9db7-3981f7c0e126/components/main/capabilities/switch/status
GET http://192.168.1.140:8088/api/forward?url=https://api.wheretheiss.at/v1/satellites/25544
GET http://192.168.1.140:8088/api/forward?url=https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature&storedquery_id=fmi::observations::weather::timevaluepair&place=helsinki
```

### Forwarding device/app message TO an Edge driver
Scenario:  The Edge driver wants to receive web requests from a LAN-based device or application

The Edge driver sends an HTTP request to the server to **register** a specific device/app address from which it wants to receive messages:
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

#### Device or Application Messages
Once the Edge driver successfully registers with the Bridge Server, the device/app that wants to get a message to a driver simply configures its GET or POST HTTP request to go to the Bridge Server itself.  Once received by the Bridge Server, if the source IP address matches an entry in its registration table, then the message will be automatically forwarded to the registered Edge driver.  In this way, the device/app never needs to know the hub IP address or driver port number.

#### Registrations & Scrubbing
A hidden file '.registrations' is maintained by the server to keep a persistant list of driver registrations.  Occassionally, Edge drivers or Edge devices may get deleted without issuing a delete registration request to the server.  As a result, orphaned registrations can exist.  However the server will periodically scrub these when it repeatedly fails to reach the registered driver.  Applicable scrub messages will be displayed by the server when this occurs and should be considered normal.
