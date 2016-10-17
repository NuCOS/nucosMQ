from __future__ import print_function
from __future__ import absolute_import
#from __future__ import all_feature_names

from collections import defaultdict
import socket
import time
from inspect import ismethod, isfunction
from threading import Thread

from .nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, EOM, SocketArray
from .nucosLogger import Logger

from .nucos23 import ispython3


class NucosClientUDP():
    """
    base NuCOS socket class on client side
    
    implements protocol on top of tcp/ip socket
    """
    logger = Logger('nucosClient', ["serverip"])
    logger.format('[%(asctime)-15s] %(name)-8s %(levelname)-7s %(serverip)s -- %(message)s')
    logger.level("INFO")
    
    def __init__(self, IP, PORT, uid = ""):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IP = IP
        self.PORT = PORT
        self.LISTEN = False
        self.uid = uid
        self.is_closed = True
            
    def start(self,timeout=60.0):
        """
        start a non-blocking listening thread
        
        
        """
        self.logger.log(lvl="DEBUG", msg="try to connect socket", serverip=self.IP)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)
        self.error = self.socket.connect_ex((self.IP, self.PORT))
        
    def is_connected(self):
        return not self.is_closed
        
    def close(self):
        """
        close existing connection
        
        
        """
        #time.sleep(1.0)
        self.LISTEN = False
        self.logger.log(lvl="DEBUG", msg="try to close existing socket")
        self.send("shutdown", "now")
        time.sleep(0.1) #waiting for an answer to stop the current listening thread
        if not self.is_closed:
            self.socket.close()
            self.is_closed = True
        
        
        
    def send(self, event, content):
        """
        send data to server, it postpones automatically after auth process
        
        a valid message has content and event.
        
        content is a dictonary of or a primitive datatype e.g.: 
        
            content = str("")
        or 
            content = {"key":content}
            
        """
        return self._send(event, content)
        
        
    def _send(self, event, content, room=''):
        """
        internal raw send command, do not use from external
        """
        if not room:
            data = { "event":event, "content":content }
        else:
            data = { "event":event, "content":content, "room":room }

        outgoing = NucosOutgoingMessage(data)        
        payload,error = outgoing.payload()
            
        if error:
            logerror = "outgoing msg error %s"%error
            self.logger.log(lvl="ERROR",msg=logerror)
            #raise Exception(logerror)
            return False
        try:    
            self.socket.send(payload)
            return True
        except socket.error as ex:
            self.logger.log(lvl="ERROR", msg="client socket error %s %s"%(ex,payload))
            #self.is_closed = True
            self.LISTEN = False
            return False
            #raise Exception("pipe broken")
        
        

            
        
        
