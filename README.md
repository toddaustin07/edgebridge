#Forwarding Bridge Server for SmartThings Edge drivers
## Forwarding Bridge Server
The forwarding bridge server (subsequently referred to as 'server') included in this repository has broader capability beyond support for this particular use case (Shelly Motion Sensor).  This section will describe *all* features, as well as highlight how it is used in this particular Shelly Motion Sensor scenario.

The server itself is simply a Python script that can be run on any 'always on' Windows/Linux/Mac/Raspberry Pi computer.  The server is provided either as a 3.7x Python source script or a Windows executable program file.  It can read an optional configuration file created by the user (see below).

The server includes these capabilities:
### 1. Forward HTTP requests from an Edge driver to any URL
Another limitation of Edge drivers is that the hub platform allows them to communicate to only **local** IP addresses.  This excludes any internet requests or other external RESTful API calls, for example.  With this solution, an Edge driver can send a request to the server to be forwarded, which the server will do and return the response back to the requesting Edge driver.  (My Web Requestor https://github.com/toddaustin07/webrequestor devices can also be used to initiate these requests)
#### SmartThings API calls
An additional capability of the server is that it recognizes requests being forwarded to the **SmartThings RESTful API**, and using the Token configured by the user, can forward those requests and return the response, allowing Edge drivers access to any SmartThings API call.  For example, this can allow a driver to get the device status of ANY SmartThings device, and use it in its logic - allowing it to perform SmartApp-like functions.
### 2. Forward messages from LAN-based devices or applications TO a specific Edge driver
As described above, Edge drivers cannot use any specific port, so this makes it impractical for other LAN-based configurable devices (e.g. Shelly Motion Sensor) or applications to be able to send messages directly *TO* an Edge driver without first establishing a unique peer-to-peer or client/server link.  This is possible, but requires more custom coding to make it work (discovery, monitoring connection, managing change, etc.).  

This server offers a simpler solution:  an Edge driver 'registers' with the server what IP address it is interested in getting messages from.  The LAN device or application is configured to send its messages to the server (which has a fixed IP/port number).  Then when the server receives those messages, it looks up who is registered to receive them, and then forwards them to the appropriate IP/port number.  If/when the Edge driver port number changes, it simply re-registers the new port number with the server.  No configuration change is needed at the LAN device or application.  A static IP address is typically recommended for the physical device or application.
## Installation

Download the Python script or Windows executable file to a folder on your computer.  You can start it manually or preferrably, configure your computer to auto start the program whenever it reboots.
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

Start the server by this command:
```
python3 edgebridge.py
```
It is recommended to run this in a window where you can monitor the output messages.  You may want to log them permanently to a file as well.

Note that the server creates and maintains a hidden file ('.registrations') which contains records capturing the Edge driver ID, hub address, and LAN device/application IP address to be monitored.  As driver port numbers change due to restarts, the registrations file may contain old records for a short time, but these will eventually be cleared out after 3 failed attempts to communicate with the 'old' port number(s).
