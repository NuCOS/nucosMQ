from .nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, EOM, SocketArray
from .nucosLogger import Logger

import socket
from .nucos23 import ispython3
from .nucosQueue import NucosQueue

from .nucosServer import NucosServer
from .nucosClient import NucosClient

class NucosLink():
    """
    base symmetric socket class (can be client or server, depending on the bind/connect call)
    
    unified api
    """
    logger = Logger('nucosLink', [])
    logger.format('[%(asctime)-15s] %(name)-8s %(levelname)-7s -- %(message)s')
    logger.level("DEBUG")
    
    def __init__(self):
        self.conn = None
        self.status = None

    def bind(self, IP, PORT, uid="anonymous", do_auth=None):
        if self.status:
            self.logger.log(lvl="ERROR", msg="link already in use, call close first to reuse") 
            return False
        self.uid=uid
        self.IP = IP
        self.PORT = PORT
        self.link = NucosServer(IP, PORT, do_auth=do_auth, single_server=True)
        self.link.start()
        self.status = "server"
        return True
        
    def connect(self, IP, PORT, uid="anonymous", on_challenge=None):
        if self.status:
            self.logger.log(lvl="ERROR", msg="link already in use, call close first to reuse")
            return False
        self.uid = uid
        self.link = NucosClient(IP, PORT, uid=uid, on_challenge=on_challenge)
        self.link.start()
        self.status = "client"
        return True
        
    def is_connected(self):
        if self.status == "server":
            if not self.conn:
                self.conn = self.link.get_conn(self.uid)
            if self.conn: 
                return True
            else:
                return False
        elif self.status == "client":
            return self.link.is_connected()
    
    def ping(self):
        if self.status == "server":
            if not self.conn:
                self.conn = self.link.get_conn(self.uid)
            if self.conn:
                return self.link.ping(self.conn)
            else:
                self.logger.log(lvl="ERROR", msg="link not established")
                return False
        elif self.status == "client":
            return self.link.ping()
        else:
            self.logger.log(lvl="ERROR", msg="link not established, call bind or connect before")
        
        
        
    def send(self, event, content):
        if self.status == "server":
            if not self.conn:
                self.conn = self.link.get_conn(self.uid)
            if self.conn:
                return self.link.send(self.conn, event, content)
            else:
                self.logger.log(lvl="ERROR", msg="link not established")
                return False
        elif self.status == "client":
            return self.link.send(event, content)
        else:
            self.logger.log(lvl="ERROR", msg="link not established, call bind or connect before")
            return False
        
    def add_event_callback(self, event, handler):
        self.link.add_event_callback(event, handler)
        
    def close(self):
        if not self.status:
            self.logger.log(lvl="DEBUG", msg="close already called")
            return
        self.logger.log(lvl="DEBUG", msg="close called")
        self.link.close()
        self.conn = None
        self.status = None
        
    
            