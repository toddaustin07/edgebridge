#
# Copyright 2021 Todd Austin
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
# DESCRIPTION
# 
# Forwarding Bridge Server to support Samsung SmartThings Edge drivers running on a SmartThings hub
# 
# Features:  
#   1. forward HTTP POST/GET requests from SmartThings hub Edge driver & return response 
#   2. forward HTTP POST/GET requests from IOT device to Edge drivers
#
# Reads 'edgebridge.conf' user config file for configuration options (server port, SmartThings Token)
# Creates and updates '.registrations' file for maintaining Edge driver registration list
#
VERSION = '1.2126122052'

import http.server
import datetime
import time
import socket
from typing import TYPE_CHECKING
import requests
import os
import platform
import configparser
import json

registrations = []
hubsenderrors = {}
regdeletelist = []
headers = {'Authorization': '',
           'Content-Type' : 'application/json'}

HTTP_OK = 200
CONFIGFILENAME = 'edgebridge.cfg'
REGSFILENAME = '.registrations'
MAXPORT = 65535
TOKEN_LENGTH = 36
DEFAULT_SERVERPORT = 8088
DEFAULT_ST_TOKEN = ''
SERVER_PORT = DEFAULT_SERVERPORT
SMARTTHINGS_TOKEN = DEFAULT_ST_TOKEN


def http_response(server, code, responsetosend):
    
    try:
        server.send_response(code)
        server.send_header("CONTENT-TYPE", 'text/xml; charset="utf-8"')
        server.send_header("DATE", datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"))
        server.send_header("SERVER", 'edgeBridge')
        server.send_header("CONTENT-LENGTH", str(len(responsetosend)))
        server.end_headers()
                
        server.wfile.write(bytes(responsetosend, 'UTF-8'))
    except:
        print (f'\033[91mHTTP Send error sending response: {responsetosend}\033[0m')
    

def proc_forward (server, method, path, arg):

    if arg.startswith('url='):
        url = path[path.index('url=')+4:]
        print (f'Sending {method} to {url}')
        
        if 'api.smartthings.com' in path:
            headers['Authorization'] = SMARTTHINGS_TOKEN
        else:
            headers['Authorization'] = ''
        
        headers['Host'] = path.split('//')[1].split('/')[0]
        headers['Accept'] = 'text/html,application/xml,application/json'
        
        try:
            if method in ['post', 'Post', 'POST']:
                r = requests.post(url, data='', headers=headers, timeout=3)
            elif method in ['get', 'Get', 'GET']:
                r = requests.get(url, data='', headers=headers, timeout=3)
        except requests.Timeout:
            print ("Internet request timed out")
            http_response(server, 502, "")
            
        if r.status_code == HTTP_OK:
            print ('Returned data:\n', r.text)
            http_response(server, 200, r.text)
            
        else:
            print (f'\033[91mHTTP error returned: {r.status_code}\033[0m')
            http_response(server, r.status_code, "")
            
    else:
        print ('\033[91mMissing URL from forward command\033[0m')
        http_response(server, 400, "")


def error_proc(hubaddr):

    key = f'{hubaddr[0]}:{hubaddr[1]}'
    
    if key in hubsenderrors:
        errcount = hubsenderrors[key]
        errcount += 1
        if errcount == 3:
            del hubsenderrors[key]
            for item in registrations:
                if item['hubaddr'] == hubaddr:
                    regdeletelist.append(item)
            
        else:
            hubsenderrors[key] = errcount
        
    else:
        hubsenderrors[key] = 1
        

def passto_hub(server, regrecord):

        hubaddr = regrecord['hubaddr'][0] + ':' + str(regrecord['hubaddr'][1])

        if regrecord['devaddr'][1] != None:
            devaddr = regrecord['devaddr'][0] + ':' + str(regrecord['devaddr'][1])
        else:
            devaddr = regrecord['devaddr'][0]

        url = 'http://' + hubaddr + '/' + devaddr + '/' + server.command + server.path
        headers['HOST'] = hubaddr

        print (f'Sending POST: {url} to {hubaddr}')

        try:
            r = requests.post(url, headers=headers, data='')

            if r.status_code == 200:
                print (f"Message forwarded to Edge ID {regrecord['edgeid']}")
            else:
                print (f"\033[91mERROR sending message to Edge hub {regrecord['hubaddr']}: {str(r.status_code)}\033[0m")
        except:
            print (f"\033[91mFAILED sending message to Edge hub {regrecord['hubaddr']}\033[0m")
            error_proc(regrecord['hubaddr'])

def verify_addr(addrstr):

    port = None

    if not addrstr:
        return False

    if ':' in addrstr:
        addrparts = addrstr.split(':')
        ip = addrparts[0]
        port = int(addrparts[1])
        print (f'Port={port}')
        if (port < 1) or (port > MAXPORT):
            print (f'\033[91mInvalid port number: {port}\033[0m')
            return False

    else:
        ip = addrstr

    if ip:
        ipparts = ip.split('.')
        if len(ipparts) == 4:
            try:
                if (0 <= int(ipparts[0]) < 256) and \
                   (0 <= int(ipparts[1]) < 256) and \
                   (0 <= int(ipparts[2]) < 256) and \
                   (0 <= int(ipparts[3]) < 256):

                    return (ip, port)
            except:
                print (f'\033[91mInvalid IP address syntax: {ipparts}\033[0m')
                NotImplemented
    print (f'\033[91mInvalid IP address: {ip}\033[0m')
    return False


def verify_ID(id):

    idprofile = [8,4,4,4,12]

    id = id.lower()
    parts = id.split('-')
    if len(parts) == len(idprofile):
        for i in range(len(parts)):
            if len(parts[i]) == idprofile[i]:
                for x in range(idprofile[i]):
                    if parts[i][x] not in ('0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f'):
                        return False
            else:
                return False
    else:
        return False

    return id


def find_reg(reglist, devaddr, edgeid):

    for index in range(len(reglist)):
        if reglist[index]['devaddr'] == devaddr:
            if reglist[index]['edgeid'] == edgeid:
                return(index)

    return None

def read_regs(regs_filename):

    file_path = os.getcwd() + os.path.sep + regs_filename

    try:
        with open(file_path,"r") as f1:

            reglist = []
            lines = f1.readlines()
            for line in lines:
                reglist.append(json.loads(line))
            return reglist
            
    except:
        print ('INFO: No existing registrations')
        return []

def write_regs(regs_filename, reglist):

    file_path = os.getcwd() + os.path.sep + regs_filename

    try:
        with open(file_path, 'w') as f1:
            for reg in reglist:
                f1.write(json.dumps(reg)+'\n')
    except:
        print ('\033[91mError saving registrations\033[0m')


def proc_register(server, method, arglist):
   
    for arg in arglist:
        if arg.startswith('devaddr='):
            devaddr = verify_addr(arg[8:])
        elif arg.startswith('hubaddr='):
            hubaddr = verify_addr(arg[8:])
        elif arg.startswith('edgeid='):
            edgeid = verify_ID(arg[7:])
        else:
            print ('\033[91mUnrecognized argument in register command\033[0m')
            http_response(server, 400, "")
            return

    if devaddr and hubaddr and edgeid:

        index = find_reg(registrations, devaddr, edgeid)

        if method in ['post', 'Post', 'POST']:
            print (f'Request to register device at {devaddr}')
            
            if index == None:
                registrations.append({'devaddr': devaddr, 'edgeid': edgeid, 'hubaddr': hubaddr})
                print ('Registration record ADDED')
               
            else:
                registrations[index] = {'devaddr': devaddr, 'edgeid': edgeid, 'hubaddr': hubaddr}
                print ('Existing registration was REPLACED')

            http_response(server, 200, "")
            
        elif method in ['delete', 'Delete', 'DELETE']:
            print (f'Request to remove registration {devaddr}')

            if index != None:
                del registrations[index]
                print (f'Registration {index} DELETED')
                http_response(server, 200, "")
            else:
                print (f'Request to remove address that is not registered: {devaddr}')
                http_response(server, 404, "")
        else:
            print (f'\033[91mInvalid method provided ({method}) for register command\033[0m')
            http_response(server, 405, "")
    else:
        print ('\033[91mMissing argument(s) in register command\033[0m')
        http_response(server, 400, "")
    
    print (f'Updated registrations: {registrations}')
    write_regs(REGSFILENAME, registrations)


def handle_requests(server, method, path, devaddraddr_tuple):

    if '?' in path:
        arg = path.split('?')
        if arg:
            endpoint = arg[0].split('/')
            arglist = arg[1].split('&')

            if endpoint[1] in ['api', 'API']:
                if endpoint[2] in ['forward','Forward','FORWARD']:
                    proc_forward(server, method, path, arglist[0])   
                        
                elif endpoint[2] in ['register','Register','REGISTER']:
                    proc_register(server, method, arglist)
                    
                else:
                    print ('\033[91mInvalid endpoint\033[0m')
                    http_response(server, 404, "")
            else:
                print ('\033[91mNot an API request\033[0m')
                http_response(server, 404, "")
        else:
            print ('\033[91mInvalid endpoint\033[0m')
            http_response(server, 400, "")
    else:
        print ('\033[91mInvalid endpoint\033[0m')
        http_response(server, 400, "")


def proc_registered_requests(server):
    
    global regdeletelist
    global registrations
    regfound = False

    # First see if this is a message from any registered devices

    for record in registrations:
        match = False
        if record['devaddr'][0] == server.client_address[0]:
            match = True
            if record['devaddr'][1]:
                if record['devaddr'][1] != server.client_address[1]:
                    match = False
            if match:
                regfound = True
                print('\n>>>>> Forwarding to SmartThings hub')
                passto_hub(server, record)
                
    if regfound:
        http_response(server, 200, "")
        
        # update registration list if exceeded pass-to-hub error threshold for any of the registration records
        # -- this ensures that old no-longer-used ip:port hub addresses get scrubbed from list
        for item in regdeletelist:   
            print (f'\nScrubbing registration record: {item}')   
            registrations.remove(item)
                
        if len(regdeletelist) > 0:
            write_regs(REGSFILENAME, registrations)
            regdeletelist.clear() 
    
        return True
    
    else:
        return False

class myHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        print ('\n**********************************************************************************')
        print ('\033[93m' + time.strftime("%c") + f'\033[0m  {self.command} command received from: {self.client_address}')
        print ('Endpoint: ', self.path)
        
        if not proc_registered_requests(self):
        
            handle_requests(self, 'POST', self.path, self.client_address)
        
        
    def do_GET(self):
        print ('\n**********************************************************************************')
        print ('\033[93m' + time.strftime("%c") + f'\033[0m  {self.command} command received from: {self.client_address}')
        print ('Endpoint: ', self.path)
        #print ('Headers:\n', self.headers)
        #if ('Content-Length' in self.headers) or ('CONTENT-LENGTH' in self.headers):
        #    self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        #    print ('Data:\n',self.data_string)
        #print ('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
        
        if not proc_registered_requests(self):
            
            handle_requests(self, 'GET', self.path, self.client_address)


    def do_DELETE(self):
        print ('\n**********************************************************************************')
        print ('\033[93m' + time.strftime("%c") + f'\033[0m  {self.command} command received from: {self.client_address}')
        print ('Endpoint: ', self.path)
        
        handle_requests(self, 'DELETE', self.path, self.client_address)


def process_config(config_filename):

    global SERVER_PORT
    global SMARTTHINGS_TOKEN

    CONFIG_FILE_PATH = os.getcwd() + os.path.sep + config_filename

    parser = configparser.ConfigParser()
    if parser.read(CONFIG_FILE_PATH):
        config_port = int(parser.get('config', 'Server_Port'))
        if (config_port > 0) and (config_port <= MAXPORT):
            SERVER_PORT = config_port
        else:
            print (f'\033[31mInvalid port from config file; using default: {DEFAULT_SERVERPORT}\033[0m')
        
        config_token = parser.get('config', 'SmartThings_Bearer_Token')
        if len(config_token) == TOKEN_LENGTH:
            SMARTTHINGS_TOKEN = 'Bearer ' + config_token
        else:
            print('\033[31mInvalid SmartThings Token from config file; assumed None\033[0m')
            SMARTTHINGS_TOKEN = DEFAULT_ST_TOKEN
    else:
        SERVER_PORT = DEFAULT_SERVERPORT
        SMARTTHINGS_TOKEN = DEFAULT_ST_TOKEN


#################################################################################################
##                  MAINLINE
#################################################################################################

if __name__ == '__main__':

    thisOS = platform.system()
    print (f'O/S = {thisOS}')
    if thisOS == 'Windows':
        os.system('color')              # force color text to work in Windows

    process_config(CONFIGFILENAME)
    registrations = read_regs(REGSFILENAME)

    HandlerClass = myHTTPRequestHandler
    ServerClass = http.server.HTTPServer

    httpd = ServerClass(('', SERVER_PORT), HandlerClass)

    if httpd:
        # Trick to get our IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        myipAddress =  s.getsockname()[0]
        s.close()

        print (f"\n\033[97mForwarding Bridge Server v{VERSION} (for SmartThings Edge)\033[0m")
        print (f"\033[94m > Serving HTTP on {myipAddress}:{SERVER_PORT}\033[0m\n")

        try: 
            httpd.serve_forever()    # wait for, and process HTTP requests

        except KeyboardInterrupt:
            print ('\n\033[92mINFO: Action interrupted by user...\033[0m\n')
    else:
        print ('\n\033[91mERROR: cannot initialize Server\033[0m\n')
