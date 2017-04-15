#!/usr/bin/env python

import socket
import threading
import sys
import os
import getopt
import subprocess
import time

SERVER_SHUTDOWN = "request server shutdown"
CLIENT_EXIT     = "client exit"
MESSAGE_RECEIVED= "1"
UPLOAD_FILE = "upload"
DOWNLOAD_FILE = "download"

class pySSH:
    """
Python NetCal Tool
Usage: python pySSH.py -t target_host -p port [OPTIONS]
  -l --listen                       listen on [host]:[port] for incoming 
                                    connections
  -e --execute=file                 execute file upon receiving connection
  -c --command                      initilize command shell
  -u --upload=destination           upload file to [destination] upon receiving 
                                    connection
"""
    def __init__(self):
        self.shortOptions = "ht:p:le:cu:"
        self.longOptions = ["help", "target", "port", "listen", "execute", "command", "upload"]
        self.LISTEN = False
        self.COMMAND = False
        self.EXECUTE=""
        self.TARGET = "0.0.0.0"
        self.PORT = 8327
        self.UPLOAD_DESTINATION = ""
    def usage(self, msg=None):
        LOG(self.__doc__)
        sys.exit(msg)
    def __call__(self, *args):
        args = [arg for arg in args]
        args.extend(sys.argv[1:])
        if not args:
            self.usage("Error: No valid arguments supplied")
        try:
            opts, args = getopt.getopt(args, self.shortOptions, self.longOptions)
        except getopt.GetoptError as optionError:
            self.usage(str(optionError))
        self.setArguments(opts)
        if self.LISTEN:
            server = Server(self.TARGET, self.PORT)
            server()
        else:
            client = Client(self.TARGET, self.PORT)
            client(self.EXECUTE)
    def setArguments(self, opts):
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                self.usage()
            elif opt in ("-t", "--target"):
                self.TARGET = arg 
            elif opt in ("-p", "--port"):
                self.PORT = int(arg)
            elif opt in ("-l", "--listen"):
                self.LISTEN = True
            elif opt in ("-e", "--execute"):
                self.EXECUTE = arg
            elif opt in ("-c", "--command"):
                self.COMMAND = True
            elif opt in ("-u", "--upload"):
                self.UPLOAD_DESTINATION = arg
            else:
                self.usage("Error: Unhandled option, opt[%s], arg[%s]" % opt, arg)


class Logger:
    TERMINAL = 0
    RAM = 1
    def __init__(self, mode=0):
        self.mode = mode
        self.data = []
    def __call__(self, msg):
        if self.mode == self.TERMINAL:
            print(msg)
        if self.mode == self.RAM:
            self.data.append(msg)
        return msg
    def clear(self):
        self.data.clear()
LOG = Logger()


def getLocalHostInfo():
    host_name = socket.gethostname()
    host_IP = socket.gethostbyname(host_name)
    LOG("Local host : %s:%s" % (host_name, host_IP))
    return (host_name, host_IP)


class Client:
    def __init__(self, ip, port):
        self.bufferSize = 4096
        self.target_host = ip
        self.target_port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((self.target_host, self.target_port))
        except:
            self.exit()
    def __call__(self, msg):
        if msg:
            #TODO
            self.getResponse()
            time.sleep(0.025)#dischard prompt
            self.client.send((msg+'\n').encode())
            if msg.lower()==SERVER_SHUTDOWN:
                self.exit()
                return
            LOG(self.getResponse())
            self.getResponse()#dischard prompt
            time.sleep(0.025)
            self.client.send((CLIENT_EXIT+'\n').encode())
        else:
            self.console()
        self.exit() 
    def exit(self):
        self.client.shutdown(socket.SHUT_RDWR)
        self.client.close()
    def getResponse(self):
        response_length = self.bufferSize
        response = ""
        while self.bufferSize <= response_length:
            data = self.client.recv(self.bufferSize)
            response_length = data.__len__()
            response += data.decode()
        self.acknowledge()
        return response
    def acknowledge(self):
        self.client.send(MESSAGE_RECEIVED.encode())
    def console(self):
        while True:
            prompt = self.getResponse()
            msg = input(prompt)
            self.client.send((msg+'\n').encode())
            if msg.lower()==CLIENT_EXIT:
                break
            if msg.lower()==SERVER_SHUTDOWN:
                break
            commands = msg.split(' ')
            if commands[0] == UPLOAD_FILE:
                filemanager = FileSender()
                filemanager.sendFile(self.client, commands[1])#TOD Verify commands have two args
            elif commands[0] == DOWNLOAD_FILE:
                filemanager = FileSender()
                filemanager.receiveFile(self.client, commands[-1])#TOD Verify commands have two args
            else:
                LOG(self.getResponse())
            

class Server:
    def __init__(self, ip, port):
        getLocalHostInfo()
        self.bufferSize = 1024
        self.prompt = "pySSH> ".encode()
        self.mainLoop = False 
        self.bind_ip = ip
        self.bind_port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.bind_ip, self.bind_port))
        self.server.listen(1)
        LOG("[*] Listening on %s:%d" % (self.bind_ip, self.bind_port))
    def handle_client(self, client_socket):
        self.console(client_socket)
    def __call__(self):
        self.mainLoop = True 
        while self.mainLoop:
            client, addr = self.server.accept()
            LOG("[*] Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target=self.handle_client, args=(client,))
            client_handler.start()
        else:
            exit()
    def exit(self):
        if self.mainLoop:
            self.mainLoopExitSequence()
        self.server.shutdown(socket.SHUT_RDWR)
        self.server.close()
    def mainLoopExitSequence(self):
        self.mainLoop = False
        try:
            lastCall = Client(self.bind_ip, self.bind_port)
            lastCall.getResponse()
            lastCall.client.send(CLIENT_EXIT.encode())
            lastCall.exit()
        except Exception as ExceptionError:
            LOG("Error mainLoopExitSequence [%s]" % str(ExceptionError))
    def runCommand(self, command):
        command = command.rstrip() #trim \n
        output = None
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            LOG(output.decode())
        except subprocess.CalledProcessError as subprocessException:
            LOG("Error: failed to execute command [%s]" % command)
            output = subprocessException.output
        return output
    def console(self, client_socket):
        if not self.mainLoop:
            client_socket.close()
            return
        while True:
            self.sendMessageToClient(client_socket, self.prompt);
            request = ""
            while '\n' not in request:
                request += client_socket.recv(self.bufferSize).decode()
            request = request.rstrip()
            LOG("[*] Received: %s" % request)
            if request.lower() == SERVER_SHUTDOWN:
                client_socket.close()
                self.exit()
                return
            if request.lower() == CLIENT_EXIT:
                client_socket.close()
                return
            self.commandParser(request, client_socket)
    def commandParser(self, request, client_socket):
        commands = request.split(' ')
        response = None
        if commands[0] == UPLOAD_FILE:
            filemanager = FileSender()
            filemanager.receiveFile(client_socket, commands[-1])#TOD Verify commands have two args
        elif commands[0] == DOWNLOAD_FILE:
            filemanager = FileSender()
            filemanager.sendFile(client_socket, commands[1])#TOD Verify commands have two args
        elif commands[0] == "cd":
            response = os.chdir(" ".join(request.split(' ')[1:]))
            self.sendMessageToClient(client_socket, response);
        else:
            response = self.runCommand(request)
            self.sendMessageToClient(client_socket, response);
    def sendMessageToClient(self, client_socket, msg):
        if not msg:
            msg = " "
        acknowledgement = False
        while not acknowledgement:
            try:
                msg = msg.encode()
            except:
                pass
            client_socket.send(msg)
            try:
                client_socket.settimeout(0.7)
                acknowledgement = client_socket.recv(self.bufferSize).decode() == MESSAGE_RECEIVED
                client_socket.settimeout(None)
            except:
                pass

class FileSender:
    def __init__(self):
        self.receiveBufferSize = 4096
    def sendFile(self, targetSocket, filename):
        with open(filename, "rb") as inputFile:
            data = inputFile.read()
            targetSocket.send(data)
    def receiveFile(self, targetSocket, filename):
        with open(filename, "wb") as outputFile:
            response_length = self.receiveBufferSize
            while self.receiveBufferSize <= response_length:
                data = targetSocket.recv(self.receiveBufferSize)
                response_length = data.__len__()
                outputFile.write(data)


if __name__ == "__main__":
    ssh = pySSH()
    ssh()
