from __future__ import print_function
from collections import defaultdict
import socket
import time
from inspect import ismethod, isfunction
from nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, EOM
from threading import Thread
from nucosLogger import Logger
import os

logger = Logger('nucosClient')
logger.format(["serverip"], '[%(asctime)-15s] %(name)-8s %(levelname)-7s %(serverip)s -- %(message)s')
logger.level("DEBUG")


no_talktome = False


class NucosClient():
    def __init__(self, IP, PORT, uid = ""):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger = logger
        #logger.log(lvl="INFO", msg="try to connect socket", serverip=IP)
        #self.error = self.socket.connect_ex((IP, PORT))
        #if self.error:
        #    logger.log(lvl="ERROR", msg="something wrong with socket: %s"%self.error, serverip=IP)
        self.IP = IP
        self.PORT = PORT
        self.LISTEN = False
        self.event_callbacks = defaultdict(list)
        self.on_connect_callbacks = []
        self.on_disconnect_callbacks = []
        LEOM = len(EOM)
        self.uid = uid
        self.is_closed = True
        #self.queue = Queue.Queue()
        
    def auth(self, uid, session_key):
        pass
        #self.eventlet.emit("auth", {"uid":uid, "session_key":session_key})
        #self.socketIO.wait(seconds=0.5)
        #self.socketIO.emit("join", {"room":"13", "username":uid})
        #self.socketIO.on('serverEvent', on_serverEvent)
          
    def start(self):
        #start a non-blocking listening thread
        logger.log(lvl="INFO", msg="try to connect socket", serverip=self.IP)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.error = self.socket.connect_ex((self.IP, self.PORT))
        if self.error:
            logger.log(lvl="ERROR", msg="something wrong with socket: %s"%self.error, serverip=self.IP)
        self.is_closed = False
        t = Thread(target=self.listen)
        t.daemon = True
        t.start()
          
    def listen(self):
        self.LISTEN = True
        logger.log(lvl="INFO", msg="start listening")
        full_msg = ''
        while True:
            msg = self.socket.recv(1024)
            if not self.LISTEN:   #outcome from the thread (TODO: testing)
                logger.log(lvl="INFO", msg="stop listening")
                return
            if msg:
                full_msg = ''.join([full_msg, msg])
                if len(msg) == 1024:
                    logger.log(lvl="DEBUG", msg="JOIN %s"%msg)
                    if not full_msg[-LEOM:] == EOM:
                        logger.log(lvl="DEBUG", msg="CONT")
                        continue                
                self.on_serverEvent(full_msg)
                full_msg = ''
            else:
                break
        logger.log(lvl="WARNING", msg="client going down")
        

    def add_event_callback(self, event, handler):
        delegate = lambda x: handler(x)
        self.event_callbacks[event].append(delegate)
        
    def add_on_connect(self, handler):
        delegate = lambda x: handler(x)
        self.on_connect_callbacks.append(delegate)
        
    def add_on_disconnect(self, handler):
        delegate = lambda x: handler(x)
        self.on_disconnect_callbacks.append(delegate)
        
    def add_on_challenge(self, handler):
        delegate = lambda x: handler(x)
        self.event_callbacks["challenge"].append(delegate)
        
    def close(self):
        #time.sleep(1.0)
        self.LISTEN = False
        logger.log(lvl="INFO", msg="try to close existing socket")
        self.send("shutdown", "now")
        time.sleep(1.0) #waiting for an answer to stop the current listening thread
        self.socket.close()
        self.is_closed = True
        
    def send(self, event, content):
        data = {"event":event, "content":content}
        outgoing = NucosOutgoingMessage(data)
        try:
            self.socket.send(outgoing.payload())
        except:
            logger.log(lvl="WARNING", msg="socket pipe broken")
            self.is_closed = True
            self.LISTEN = False
            raise Exception("pipe broken")
        
    def prepare_auth(self, uid, on_challenge=None):
        if isfunction(on_challenge) or ismethod(on_challenge):
            self.add_on_challenge(on_challenge)
        else:
            raise Exception("no on_challenge method or function available")
        self.uid = uid
        
    def on_serverEvent(self, payload):
        incoming = NucosIncomingMessage(payload)
        
        logger.log(lvl="DEBUG", msg="incoming payload: %s  "%payload)
        msgs, error = incoming.msgs()
        if error:
            logger.log(lvl="WARNING", msg="error in incoming message: %s"%error)
        for msg in msgs: #from server always event, content form is valid
            event = msg["event"]
            content = msg["content"]
            logger.log(lvl="INFO", msg="incoming serverEvent: %s | %s"%(event, content))
            if event == "shutdown":
                #time.sleep(0.1)
                data = {"event":"shudown", "content":"confirmed"}
                outgoing = NucosOutgoingMessage(data)
                self.socket.send(outgoing.payload())
                return
            if event == "start_auth":
                logger.log(lvl="WARNING", msg="try to react on start_auth")
                if self.uid:
                    data = {"event":"uid", "content":self.uid}
                    outgoing = NucosOutgoingMessage(data)
                    self.socket.send(outgoing.payload())
                    #logger.log(lvl="WARNING", msg="try to react")
                else:
                    logger.log(lvl="WARNING", msg="no prepare_auth yet called, therefore no uid on hand, auth failed")
                    raise Exception("no prepare_auth yet called, therefore no uid on hand, auth failed")
            elif event == "challenge_auth":
                signature = self.event_callbacks["challenge"][0](content)
                data = {"event":"signature", "content":signature}
                outgoing = NucosOutgoingMessage(data)
                self.socket.send(outgoing.payload())
            elif event == "auth_final":
                if content == "success":
                    logger.log(lvl="INFO", msg="socket auth_final: %s"%content)
                    self.send("thanks","i am in")
                else:
                    logger.log(lvl="WARNING", msg="socket auth failed")
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
            
        
        