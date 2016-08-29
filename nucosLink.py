from .nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, EOM, SocketArray
from .nucosLogger import Logger

import socket
from .nucos23 import ispython3
from .nucosQueue import NucosQueue

from nucosMQ import NucosServer
from nucosMQ import NucosClient

class NucosLink():
    """
    base symmetric socket class (can be client or server, depending on the bind/connect call)
    
    unified api
    """
    logger = Logger('nucosLink')
    logger.format([], '[%(asctime)-15s] %(name)-8s %(levelname)-7s -- %(message)s')
    logger.level("DEBUG")
    
    def __init__(self):
        self.conn = None
        self.status = None

    def bind(self, IP, PORT, uid="anonymous", do_auth=None):
        if self.status:
            self.logger.log(lvl="ERROR", msg="link already in use, call close first to reuse") 
            return
        self.uid=uid
        self.IP = IP
        self.PORT = PORT
        self.link = NucosServer(IP, PORT, do_auth=do_auth, single_server=True)
        self.link.start()
        self.status = "server"
        
    def connect(self, IP, PORT, uid="anonymous", on_challenge=None):
        if self.status:
            self.logger.log(lvl="ERROR", msg="link already in use, call close first to reuse")
            return
        self.uid = uid
        self.link = NucosClient(IP, PORT, uid=uid, on_challenge=on_challenge)
        self.link.start()
        self.status = "client"
        
    def is_connected(self):
        pass
    
    def ping(self):
        if self.status == "server":
            if not self.conn:
                self.conn = self.link.get_conn(self.uid)
            self.link.ping(self.conn)
        elif self.status == "client":
            self.link.ping()
        else:
            self.logger.log(lvl="ERROR", msg="link not established, call bind or connect before")
        
    def send(self, event, content):
        if self.status == "server":
            if not self.conn:
                self.conn = self.link.get_conn(self.uid)
            try:
                self.link.send_via_conn(self.conn, event, content)
            except:
                self.logger.log(lvl="ERROR", msg="link not established")
                return
        elif self.status == "client":
            self.link.send(event, content)
        else:
            self.logger.log(lvl="ERROR", msg="link not established, call bind or connect before")

    def add_event_callback(self, event, handler):
        self.link.add_event_callback(event, handler)
        
    def close(self):
        self.logger.log(lvl="DEBUG", msg="close called")
        self.link.close()
        self.status = None
        
    
            