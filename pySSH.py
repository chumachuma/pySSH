import socket
import threading
import sys
import getopt

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
    def usage(self, msg=None):
        LOG(self.__doc__)
        sys.exit(msg)
    def __call__(self):
        if not sys.argv[1:]:
            self.usage("Error: No valid arguments supplied")
        try:
            opts, args = getopt.getopt(sys.argv[1:], self.shortOptions, self.longOptions)
        except getopt.GetoptError as optionError:
            self.usage(str(optionError))
        self.setArguments(opts)
    def setArguments(self, opts):
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                self.usage()
            elif opt in ("-t", "--target"):
                self.TARGET = arg 
            elif opt in ("-p", "--port"):
                self.PORT = arg
            elif opt in ("-l", "--listen"):
                s = server()
                s.start()
                #self.DO_LISTEN = True
            elif opt in ("-e", "--execute"):
                client()
                #self.EXECUTE = arg
            elif opt in ("-c", "--command"):
                self.DO_COMMAND = True
            elif opt in ("-u", "--upload"):
                self.UPLOAD_DESTINATION = arg
            else:
                self.usage("Error: Unhandled option, opt[%s], arg[%s]" % opt, arg)

class logger:
    TERMINAL = 0
    def __init__(self, mode=0):
        self.mode = mode
    def __call__(self, msg):
        if self.mode == self.TERMINAL:
            print(msg)
LOG = logger()

def getLocalHostInfo():
    host_name = socket.gethostname()
    host_IP = socket.gethostbyname(hostname)
    LOG("Local host : %s:%s" % (host_name, host_IP))
    return (host_name, host_IP)

def client():
    target_host = "0.0.0.0"
    target_port = 8327
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((target_host, target_port))
    client.send("Client says Hello World".encode())
    response = client.recv(4096)
    LOG(response.decode())


class server:
    def __init__(self):
        self.bind_ip = "0.0.0.0"
        self.bind_port = 8327
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.bind_ip, self.bind_port))
        self.server.listen(1)
        LOG("[*] Listening on %s:%d" % (self.bind_ip, self.bind_port))
    def handle_client(self, client_socket):
        request = client_socket.recv(1024)
        LOG("[*] Received: %s" % request.decode())
        client_socket.send("ACK!".encode())
        client_socket.close()
    def start(self):
        while True:
            client, addr = self.server.accept()
            LOG("[*] Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target=self.handle_client, args=(client,))
            client_handler.start()
            
if __name__ == "__main__":
    ssh = pySSH()
    ssh()
