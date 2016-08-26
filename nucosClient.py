from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict
import socket
import time
from inspect import ismethod, isfunction
from threading import Thread

from .nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, EOM, SocketArray
from .nucosLogger import Logger

from .nucos23 import ispython3

no_talktome = False

class NucosClient():
    """
    base NuCOS socket class on client side
    
    implements protocol on top of tcp/ip socket
    """
    logger = Logger('nucosClient')
    logger.format(["serverip"], '[%(asctime)-15s] %(name)-8s %(levelname)-7s %(serverip)s -- %(message)s')
    logger.level("DEBUG")
    
    def __init__(self, IP, PORT, uid = ""):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IP = IP
        self.PORT = PORT
        self.LISTEN = False
        self.event_callbacks = defaultdict(list)
        self.on_connect_callbacks = []
        self.on_disconnect_callbacks = []
        self.uid = uid
        self.is_closed = True
        #self.queue = Queue.Queue()
          
    def start(self,timeout=5.0):
        """
        start a non-blocking listening thread
        
        
        """
        self.logger.log(lvl="INFO", msg="try to connect socket", serverip=self.IP)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.error = self.socket.connect_ex((self.IP, self.PORT))
        if self.error:
            self.logger.log(lvl="ERROR", msg="something wrong with socket: %s"%self.error, serverip=self.IP)
        self.is_closed = False
        t = Thread(target=self._listen)
        t.daemon = True
        t.start()
          
    def _listen(self):
        """
        receive socket raw data
        
        handle socket errors
        """
        self.LISTEN = True
        self.logger.log(lvl="INFO", msg="start listening")
        
        full_msg = SocketArray()
        
        while True:
            msg = SocketArray()
            try:            
                msg = self.socket.recv(1024)
            except socket.timeout:
                #TODO check if server is still connected 
                pass
            
            if not self.LISTEN:   #outcome from the thread (TODO: testing)
                self.logger.log(lvl="INFO", msg="stop listening")
                return
            if msg:
                full_msg = full_msg.ext(msg)
                    
                if len(msg) == 1024:
                    self.logger.log(lvl="DEBUG", msg="JOIN %s"%msg)
                    if not full_msg.endswith(EOM):
                        self.logger.log(lvl="DEBUG", msg="CONT")
                        continue                
                self._on_serverEvent(full_msg)
                full_msg = SocketArray()
            else:
                break
        self.logger.log(lvl="WARNING", msg="client going down")
        

    def add_event_callback(self, event, handler):
        """
        adds an external function or method as a callback for an incoming event
        
        if event is "all" the callback will be called for every event        
        the argument of an callback is the content
        
            def my_callback(content):
                print(content)
                
            Client.add_event_callback("should print content",my_callback)
        
        """
        delegate = lambda x: handler(x)
        self.event_callbacks[event].append(delegate)
        
    def add_on_connect(self, handler):
        """
        
        """
        delegate = lambda x: handler(x)
        self.on_connect_callbacks.append(delegate)
        
    def add_on_disconnect(self, handler):
        """
        
        """
        delegate = lambda x: handler(x)
        self.on_disconnect_callbacks.append(delegate)
        
    def _add_on_challenge(self, handler):
        delegate = lambda x: handler(x)
        self.event_callbacks["challenge"].append(delegate)
        
    def close(self):
        """
        close protocol of socket
        
        
        """
        #time.sleep(1.0)
        self.LISTEN = False
        self.logger.log(lvl="INFO", msg="try to close existing socket")
        self.send("shutdown", "now")
        time.sleep(1.0) #waiting for an answer to stop the current listening thread
        self.socket.close()
        self.is_closed = True
        
    def send(self, event, content):
        """
        send data to server
        
        a valid message has content and event.
        
        content is a dictonary of or a primitive datatype e.g.: 
        
            content = str("")
        or 
            content = {"key":content}
            
        """
        data = {"event":event, "content":content}
        outgoing = NucosOutgoingMessage(data)
        
        payload,error = outgoing.payload()
            
        if error:
            logerror = "outgoing msg error %s"%error
            self.logger.log(lvl="ERROR",msg=logerror)
            raise Exception(logerror)            
            
        try:    
            self.socket.send(payload)
        except:
            self.logger.log(lvl="WARNING", msg="socket pipe broken")
            self.is_closed = True
            self.LISTEN = False
            raise Exception("pipe broken")
        
    def prepare_auth(self, uid, on_challenge=None):
        """
        initialize the client side of the general authentification protocol
        
        on_challenge is signature delivering function with the content as argument, see self.send().
        """
        if isfunction(on_challenge) or ismethod(on_challenge):
            self._add_on_challenge(on_challenge)
        else:
            raise Exception("no on_challenge method or function available")
        self.uid = uid
        
    def _on_serverEvent(self, payload):
        """
        is called automatically and processes each incoming Message
        
        internal events:
        ----------------
        
        shutdown
        start_auth
        challenge_auth
        auth_final
        
        """
        incoming = NucosIncomingMessage(payload)
        
        self.logger.log(lvl="DEBUG", msg="incoming payload: %s  "%payload)
        msgs, error = incoming.msgs()
        if error:
            self.logger.log(lvl="WARNING", msg="error in incoming message: %s"%error)
        for msg in msgs: #from server always event, content form is valid
            event = msg["event"]
            content = msg["content"]
            self.logger.log(lvl="INFO", msg="incoming serverEvent: %s | %s"%(event, content))
            if event == "shutdown":
                #time.sleep(0.1)
                self.send("shutdown","confirmed")
                
                return
            if event == "start_auth":
                self.logger.log(lvl="WARNING", msg="try to react on start_auth")
                if self.uid:
                    self.send("uid",self.uid)
                    self.logger.log(lvl="DEBUG", msg="try to react to start auth")
                else:
                    self.logger.log(lvl="WARNING", msg="no prepare_auth yet called, therefore no uid on hand, auth failed")
                    raise Exception("no prepare_auth yet called, therefore no uid on hand, auth failed")
            elif event == "challenge_auth":
                signature = self.event_callbacks["challenge"][0](content)
                self.send("signature",signature)
                
            elif event == "auth_final":
                if content == "success":
                    self.logger.log(lvl="INFO", msg="socket auth_final: %s"%content)
                    self.send("thanks","i am in")
                else:
                    self.logger.log(lvl="WARNING", msg="socket auth failed")
                    self.close()
                    #raise Exception
            else:
                for _event, funcs in self.event_callbacks.items():
                    if _event == "all":
                        for f in funcs: 
                            f(content)
                    elif _event == event:
                        for f in funcs:
                            f(content)
                    else:
                        continue
            
        
        