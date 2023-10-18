#
# Copyright 2021, 2022, 2023 Todd Austin
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
VERSION = '1.2318101200'

import http.server
import datetime
import time
import socket
from typing import TYPE_CHECKING
import requests
import os
import sys
import platform
import configparser
import json
import ipaddress

registrations = []
hubsenderrors = {}
regdeletelist = []

HTTP_OK = 200
CONFIGFILENAME = 'edgebridge.cfg'
REGSFILENAME = '.registrations'
LOGFILE = 'edgebridge.log'
MAXPORT = 65535
TOKEN_LENGTH = 36
DEFAULT_SERVERPORT = 8088
DEFAULT_ST_TOKEN = ''
SERVER_PORT = DEFAULT_SERVERPORT
SMARTTHINGS_TOKEN = DEFAULT_ST_TOKEN
FWTIMEOUT = 5


class logger(object):
    
    def __init__(self, toconsole, tofile, fname, append):
    
        self.toconsole = toconsole
        self.savetofile = tofile

        self.os = platform.system()
        if self.os == 'Windows':
            os.system('color')
        
        if tofile:
            self.filename = fname
            if not append:
                try:
                    os.remove(fname)
                except:
                    pass
            
    def __savetofile(self, msg):
        
        with open(self.filename, 'a') as f:
            f.write(f'{time.strftime("%c")}  {msg}\n')
    
    def __outputmsg(self, colormsg, plainmsg):
        
        if self.toconsole:
            print (colormsg)
        if self.savetofile:
            self.__savetofile(plainmsg)
    
    def info(self, msg):
        colormsg = f'\033[33m{time.strftime("%c")}  \033[96m{msg}\033[0m'
        self.__outputmsg(colormsg, msg)
        
    def warn(self, msg):
        colormsg = f'\033[33m{time.strftime("%c")}  \033[93m{msg}\033[0m'
        self.__outputmsg(colormsg, msg)
        
    def error(self, msg):
        colormsg = f'\033[33m{time.strftime("%c")}  \033[91m{msg}\033[0m'
        self.__outputmsg(colormsg, msg)
        
    def hilite(self, msg):
        colormsg = f'\033[33m{time.strftime("%c")}  \033[97m{msg}\033[0m'
        self.__outputmsg(colormsg, msg)
        
    def debug(self, msg):
        if len(sys.argv) > 1:
            if sys.argv[1] == '-d':
                colormsg = f'\033[33m{time.strftime("%c")}  \033[37m{msg}\033[0m'
                self.__outputmsg(colormsg, msg)


def http_response(server, code, responsetosend):
    
    try:
        server.send_response(code)
        if len(responsetosend) > 0:
            server.send_header("Content-Type", 'text/xml; charset="utf-8"')
            server.send_header("Content-Length", str(len(bytes(responsetosend, 'UTF-8'))))
        server.send_header("Date", datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"))
        server.send_header("Server", 'edgeBridge')
        
        server.end_headers()
                
        server.wfile.write(bytes(responsetosend, 'UTF-8'))
        log.debug ('Response sent')
    except:
        log.error (f'HTTP Send error sending response: {responsetosend}')
    

def build_headers(server, path):

    headers = {}

    ignored = ['user-agent', 'host', 'te', 'connection']

    for key, value in server.headers.items():
        if key.lower() not in ignored:
            headers[key] = value

    if 'api.smartthings.com' in path:
        if 'authorization' not in map(str.lower, server.headers.keys()):
            if len(SMARTTHINGS_TOKEN) > 0:
                headers['Authorization'] = SMARTTHINGS_TOKEN
        
    headers['Host'] = path.split('//')[1].split('/')[0]
    
    if 'accept' not in map(str.lower, server.headers.keys()):
        headers['Accept'] = '*/*'
        
    headers['User-Agent'] = 'SmartThings Edge Hub'
    
    if server.data_bytes != None:
        if len(server.data_bytes) > 0:
            headers['Content-Length'] = str(len(server.data_bytes))
        
    return headers
    

def proc_forward (server, method, path, arg):

    headers = {}

    if arg.startswith('url='):
        url = path[path.index('url=')+4:]
        log.info (f'Sending {method} to {url}')
        
        headers = build_headers(server, path)
                
        log.debug (f'Headers: {headers}')
        if server.data_bytes:
            log.debug (f'Body: {server.data_bytes.decode("utf-8")}')
        
        try:
            lc_method = method.lower()
            if lc_method in ['post', 'put', 'get']:
                r = getattr(requests, lc_method)(url, data=server.data_bytes, headers=headers, timeout=FWTIMEOUT)
            
            #if method in ['post', 'Post', 'POST']:
            #    r = requests.post(url, data=server.data_bytes, headers=headers, timeout=FWTIMEOUT)
            #elif method in ['put', 'Put', 'PUT']:
            #    r = requests.put(url, data=server.data_bytes, headers=headers, timeout=FWTIMEOUT)
            #elif method in ['get', 'Get', 'GET']:
            #    r = requests.get(url, data=server.data_bytes, headers=headers, timeout=FWTIMEOUT)
        except requests.Timeout:
            log.error ("Internet request timed out")
            http_response(server, 502, "")
            return
            
        if r.status_code == HTTP_OK:
            
            log.debug (f'Returned data: {r.text}')
            http_response(server, 200, r.text)
            log.info (f'Response returned to Edge driver (bytes len={len(bytes(r.text, "UTF-8"))})')
            
        else:
            log.warn (f'HTTP error returned: {r.status_code}')
            http_response(server, r.status_code, "")
            
    else:
        log.error ('Missing URL from forward command')
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

        headers = {}

        hubaddr = regrecord['hubaddr'][0] + ':' + str(regrecord['hubaddr'][1])

        if regrecord['devaddr'][1] != None:
            devaddr = regrecord['devaddr'][0] + ':' + str(regrecord['devaddr'][1])
        else:
            devaddr = regrecord['devaddr'][0]

        url = 'http://' + hubaddr + '/' + devaddr + '/' + server.command + server.path
        headers['Host'] = hubaddr
        
        if server.data_bytes != None:
            if len(server.data_bytes) > 0:
                headers['Content-Length'] = str(len(server.data_bytes))
                if 'Content-Type' in server.headers:
                    headers['Content-Type'] = server.headers['Content-Type']
                

        log.info (f'Sending POST: {url} to {hubaddr}')

        try:
            r = requests.post(url, headers=headers, data=server.data_bytes)

            if r.status_code == 200:
                log.info (f"Message forwarded to Edge ID {regrecord['edgeid']}")
            else:
                log.error (f"ERROR sending message to Edge hub {regrecord['hubaddr']}: {str(r.status_code)}")
        except:
            log.error (f"FAILED sending message to Edge hub {regrecord['hubaddr']}")
            error_proc(regrecord['hubaddr'])

def verify_addr(addrstr):

    port = None

    if not addrstr:
        return False

    if ':' in addrstr:
        addrparts = addrstr.split(':')
        ip = addrparts[0]
        port = int(addrparts[1])
        #print (f'Port={port}')
        if (port < 1) or (port > MAXPORT):
            log.error (f'Invalid port number: {port}')
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
                log.error (f'Invalid IP address syntax: {ipparts}')
                NotImplemented
                
    log.error (f'Invalid IP address: {ip}')
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
        log.warn ('INFO: No existing registrations')
        return []

def write_regs(regs_filename, reglist):

    file_path = os.getcwd() + os.path.sep + regs_filename

    try:
        with open(file_path, 'w') as f1:
            for reg in reglist:
                f1.write(json.dumps(reg)+'\n')
    except:
        log.error ('Error saving registrations')


def proc_register(server, method, arglist):
   
    for arg in arglist:
        if arg.startswith('devaddr='):
            devaddr = verify_addr(arg[8:])
        elif arg.startswith('hubaddr='):
            hubaddr = verify_addr(arg[8:])
        elif arg.startswith('edgeid='):
            edgeid = verify_ID(arg[7:])
        else:
            log.error ('Unrecognized argument in register command')
            http_response(server, 400, "")
            return

    if devaddr and hubaddr and edgeid:

        index = find_reg(registrations, devaddr, edgeid)

        if method in ['post', 'Post', 'POST']:
            log.info (f'Request to register device at {devaddr}')
            
            if index == None:
                registrations.append({'devaddr': devaddr, 'edgeid': edgeid, 'hubaddr': hubaddr})
                log.info ('Registration record ADDED')
               
            else:
                registrations[index] = {'devaddr': devaddr, 'edgeid': edgeid, 'hubaddr': hubaddr}
                log.info ('Existing registration was REPLACED')

            http_response(server, 200, "")
            
        elif method in ['delete', 'Delete', 'DELETE']:
            log.info (f'Request to remove registration {devaddr}')

            if index != None:
                del registrations[index]
                log.info (f'Registration {index} DELETED')
                http_response(server, 200, "")
            else:
                log.warn (f'Request to remove address that is not registered: {devaddr}')
                http_response(server, 404, "")
        else:
            log.error (f'Invalid method provided ({method}) for register command')
            http_response(server, 405, "")
    else:
        log.error ('Missing argument(s) in register command')
        http_response(server, 400, "")
    
    log.info (f'Updated registrations: {registrations}')
    write_regs(REGSFILENAME, registrations)


def handle_requests(server):
    
    method = server.command
    path = server.path

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
                    log.warn ('Invalid endpoint')
                    http_response(server, 404, "")
            else:
                log.error ('Not an API request')
                http_response(server, 404, "")
        else:
            log.error ('Invalid endpoint')
            http_response(server, 400, "")
    else:
        log.error ('Unregistered address or Invalid endpoint')
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
                log.info('>>>>> Forwarding to SmartThings hub')
                passto_hub(server, record)
                
    if regfound:
        http_response(server, 200, "")
        
        # update registration list if exceeded pass-to-hub error threshold for any of the registration records
        # -- this ensures that old no-longer-used ip:port hub addresses get scrubbed from list
        for item in regdeletelist:   
            log.info (f'Scrubbing registration record: {item}')   
            registrations.remove(item)
                
        if len(regdeletelist) > 0:
            write_regs(REGSFILENAME, registrations)
            regdeletelist.clear() 
    
        return True
    
    else:
        return False
        
        
def proc_msg(server):
        
    log.info ('**********************************************************************************')
    log.info (f'{server.command} request received from: {server.client_address}')
    log.debug (f'Endpoint: {server.path}')
    
    server.data_bytes = None
    if 'Content-Length' in server.headers:
        server.data_bytes = server.rfile.read(int(server.headers['Content-Length']))
        
    if not proc_registered_requests(server):
        handle_requests(server)


class myHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        
        # If a ping, just send response and don't display any messages
        if '/api/ping' in self.path:
            log.debug ('Pingreq')
            http_response(self, 200, "")
            return
        
        else:
            proc_msg(self)
            
            
    def do_PUT(self):
        
        proc_msg(self)
        
        
    def do_GET(self):
        
        proc_msg(self)
        

    def do_DELETE(self):
        
        proc_msg(self)
        

    def log_message(self, format, *args):
        return


def process_config(config_filename):

    global SERVER_PORT
    global SERVER_IP
    global SMARTTHINGS_TOKEN
    global log
    
    SERVER_IP = ''
    SERVER_PORT = DEFAULT_SERVERPORT
    SMARTTHINGS_TOKEN = DEFAULT_ST_TOKEN
    conoutp = True
    logoutp = False
    LOGFILE = ''

    CONFIG_FILE_PATH = os.getcwd() + os.path.sep + config_filename

    parser = configparser.ConfigParser()
    if parser.read(CONFIG_FILE_PATH):
        
        try:
            config_ip = parser.get('config', 'Server_IP')
            try:
                config_ip = ipaddress.ip_address(parser.get('config', 'Server_IP'))
                SERVER_IP = config_ip
            except ValueError:
                print (f'\n\033[93mInvalid Server IP address in config file; using detected IP\033[0m\n')
            
        except:
            pass
        
        try:
            config_port = int(parser.get('config', 'Server_Port'))
            if (config_port > 0) and (config_port <= MAXPORT):
                SERVER_PORT = config_port
            else:
                print (f'\033[31mInvalid port from config file; using default: {DEFAULT_SERVERPORT}\033[0m')
        except:
            print (f'\033[31mMissing port from config file; using default: {DEFAULT_SERVERPORT}\033[0m')
            
        try:
            config_token = parser.get('config', 'SmartThings_Bearer_Token')
            if len(config_token) == TOKEN_LENGTH:
                SMARTTHINGS_TOKEN = 'Bearer ' + config_token
            else:
                print('\033[31mInvalid SmartThings Token from config file; assumed None\033[0m')
                SMARTTHINGS_TOKEN = DEFAULT_ST_TOKEN
        except:
            pass
           
        try:    
            if parser.get('config', 'forwarding_timeout'):
                FWTIMEOUT = int(parser.get('config', 'forwarding_timeout'))
        except:
            pass
        
        try:
            if parser.get('config', 'console_output').lower() == 'yes':
                conoutp = True
            else:
                conoutp = False

            if parser.get('config', 'logfile_output').lower() == 'yes':
                logoutp = True
                LOGFILE = parser.get('config', 'logfile')
            else:
                logoutp = False
                LOGFILE = ''
        except:
            print ('Using output config defaults')
            
    log = logger(conoutp, logoutp, LOGFILE, False)
    

#################################################################################################
##                  MAINLINE
#################################################################################################

if __name__ == '__main__':

    thisOS = platform.system()
    #print (f'O/S = {thisOS}')
    if thisOS == 'Windows':
        os.system('color')              # force color text to work in Windows


    process_config(CONFIGFILENAME)
    registrations = read_regs(REGSFILENAME)

    HandlerClass = myHTTPRequestHandler
    ServerClass = http.server.HTTPServer

    try:
        httpd = ServerClass((str(SERVER_IP), SERVER_PORT), HandlerClass)
    except OSError as error :
        log.error (f'ERROR: cannot initialize Server; {error}')
        log.warn (f'Invalid IP address or Port {SERVER_PORT} may be in use by another application\n')
        httpd = False

    if httpd:
        if SERVER_IP == '':
            # Trick to get our IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            SERVER_IP =  s.getsockname()[0]
            s.close()

        log.hilite (f"Forwarding Bridge Server v{VERSION} (for SmartThings Edge)")
        log.hilite (f" > Serving HTTP on {SERVER_IP}:{SERVER_PORT}")

        try: 
            httpd.serve_forever()    # wait for, and process HTTP requests

        except KeyboardInterrupt:
            log.warn ('INFO: Application interrupted by user...\n')
