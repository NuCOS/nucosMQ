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
from .nucosQueue import NucosQueue



class NucosClient():
    """
    base NuCOS socket class on client side
    
    implements protocol on top of tcp/ip socket
    """
    logger = Logger('nucosClient', ["serverip"])
    logger.format('[%(asctime)-15s] %(name)-8s %(levelname)-7s %(serverip)s -- %(message)s')
    logger.level("INFO")
    
    def __init__(self, IP, PORT, uid = "", on_challenge=None, ping_timeout = 20.0):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IP = IP
        self.PORT = PORT
        self.LISTEN = False
        self.event_callbacks = defaultdict(list)
        self.room_event_callbacks = defaultdict(dict)
        self.on_connect_callbacks = []
        self.on_disconnect_callbacks = []
        self.uid = uid
        self.is_closed = True
        self.send_later = []
        self.in_auth_process = False
        self.queue = NucosQueue()
        self.ping_timeout = ping_timeout
        if on_challenge:
            if isfunction(on_challenge) or ismethod(on_challenge):
                self._add_on_challenge(on_challenge)
            else:
                raise Exception("no on_challenge method or function available")
        else:
            self.in_auth_process = False
            
    def start(self,timeout=60.0):
        """
        start a non-blocking listening thread
        
        
        """
        self.logger.log(lvl="DEBUG", msg="try to connect socket", serverip=self.IP)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.error = self.socket.connect_ex((self.IP, self.PORT))
        if self.error:
            self.logger.log(lvl="ERROR", msg="something wrong with socket: %s"%self.error, serverip=self.IP)
            return
        self.is_closed = False
        t = Thread(target=self._listen)
        t.daemon = True
        t.start()
        time.sleep(0.2) #startup time for client
          
    def _listen(self):
        """
        receive socket raw data
        
        handle socket errors
        """
        self.LISTEN = True
        self.logger.log(lvl="DEBUG", msg="start listening")
        
        fullData = SocketArray()
        while True:
            try:
                receivedData = SocketArray(self.socket.recv(1024))
            except socket.timeout:
                self.logger.log(lvl="WARNING", msg="client socket timeout")
                self.ping_later(0.2)
                continue
            except socket.error as ex:
                self.logger.log(lvl="WARNING", msg="client socket error %s"%ex)
                receivedData = SocketArray.empty()
            except ex:
                self.logger.log(lvl="WARNING", msg="another exception occured %s"%ex)
            if not self.LISTEN:
                self.logger.log(lvl="DEBUG", msg="stop listening")
                receivedData = SocketArray.empty()
            if receivedData:
                fullData = fullData.ext(receivedData)
                if len(receivedData) == 1024:
                    self.logger.log(lvl="DEBUG", msg="max length 1024 %s"%receivedData)
                    if not fullData.endswith(EOM):
                        self.logger.log(lvl="DEBUG", msg="continue listening")
                        continue                
                self._on_serverEvent(fullData)
                fullData = SocketArray()
            else:
                break
        self.logger.log(lvl="WARNING", msg="client going down")
        #here okay to call??? ->  
        if not self.is_closed:
            self.socket.close()
            self.is_closed = True
        
    def is_connected(self):
        return not self.is_closed

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
        
    def add_room_callback(self, room, handler):
        self.add_room_event_callback(room, "all", handler)
        
    def add_room_event_callback(self, room, event, handler):
        delegate = lambda x: handler(x)
        if event in self.room_event_callbacks[room].keys():
            self.room_event_callbacks[room][event].append(delegate)
        else:
            self.room_event_callbacks[room].update({event:[delegate]})
        
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
        
    def ping(self):
        """
        send a ping event and wait for a pong (blocking call, since it expects the answer right away)
        """
        start_time = time.time()
        while self.in_auth_process:
            tau = time.time()-start_time
            time.sleep(0.1)
            if tau > self.ping_timeout:
                return False
        self.logger.log(lvl="INFO", msg="send a ping, expects a pong")
        self.send("ping", "")
        self.queue.put_topic("ping-client","wait")
        msg = self.queue.get_topic("pong-client", timeout=10.0)
        if msg == "done":
            return True
        else:
            return False

    def ping_later(self, tau):
        """
        sends an asynchronious ping to return to listening thread
        """
        def ping_later(tau):
            time.sleep(tau)
            if not self.ping():
                self.close()
        t = Thread(target=ping_later, args=(tau,)) 
        t.start()
        
        
    def send(self, event, content):
        """
        send data to server, it postpones automatically after auth process
        
        a valid message has content and event.
        
        content is a dictonary of or a primitive datatype e.g.: 
        
            content = str("")
        or 
            content = {"key":content}
            
        """
        if self.in_auth_process:
            self.send_later.append((event,content,''))
            self.logger.log(lvl="WARNING", msg="no send during auth: %s %s"%(event,content))
            return
        return self._send(event, content)
        
        
    def _send(self, event, content, room=''):
        """
        internal raw send command, do not use from external since it may confuse the auth process
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
        
    def publish(self, room, event, content):
        if self.in_auth_process:
            self.send_later.append((event,content,room))
            self.logger.log(lvl="WARNING", msg="no send during auth: %s %s %s"%(event,content,room))
            return
        return self._send(event, content, room)
    
    def subscripe(self, room):
        self.send("subscripe", room)
        
    def _flush(self):
        """
        send all messages which are in the message queue and not processed yet for some reason, e.g. because of auth process
        """
        for event,content,room in self.send_later:
            self.send(event,content,room)
        self.send_later = []
        
    def _on_serverEvent(self, payload):
        """
        is called automatically and processes each incoming Message
        
        internal events:
        ----------------
        
        shutdown
        start_auth
        challenge_auth
        auth_final
        ping
        pong
        
        """
        incoming = NucosIncomingMessage(payload)
        self.logger.log(lvl="DEBUG", msg="incoming payload: %s  "%payload)
        msgs, error = incoming.msgs()
        if error:
            self.logger.log(lvl="WARNING", msg="error in incoming message: %s"%error)
        for msg in msgs: #from server always event, content form is valid
            event = msg["event"]
            content = msg["content"]
            if 'room' in msg.keys():
                room = msg["room"]
            else:
                room = ""
            self.logger.log(lvl="DEBUG", msg="incoming serverEvent: %s | %s | %s"%(event, content, room))
            if event == "shutdown":
                #time.sleep(0.1)
                self.send("shutdown","confirmed")
                return
            if event == "start_auth":
                self.in_auth_process = True
                self.logger.log(lvl="DEBUG", msg="try to react on start_auth")
                if self.uid:
                    self._send("uid",self.uid)
                    self.logger.log(lvl="DEBUG", msg="try to react to start auth")
                else:
                    self.logger.log(lvl="WARNING", msg="no prepare_auth yet called, therefore no uid on hand, auth failed")
                    raise Exception("no prepare_auth yet called, therefore no uid on hand, auth failed")
            elif event == "challenge_auth":
                signature = self.event_callbacks["challenge"][0](content)
                self._send("signature",signature)
            elif event == "auth_final":
                if content == "success":
                    self.logger.log(lvl="DEBUG", msg="socket auth_final: %s"%content)
                    self._send("thanks","i am in")
                    self.in_auth_process = False
                    self._flush()
                else:
                    self.logger.log(lvl="WARNING", msg="socket auth failed")
                    self.close()
            elif event == "ping":
                self.send("pong", "")
            elif event == "pong":
                msg = self.queue.get_topic("ping-client", timeout=10.0)
                if not msg == "wait":
                    self.logger.log(lvl="ERROR", msg="pong received no ping send %s"%msg)
                self.logger.log(lvl="INFO", msg="pong received")
                self.queue.put_topic("pong-client", "done")
            else:
                #if room: #prevents the event_callbacks
                for _room, func_dicts in self.room_event_callbacks.items():
                    if _room == room:
                        for _event, funcs in func_dicts.items():
                            if _event == "all":
                                for f in funcs: 
                                    f(content)
                            elif _event == event:
                                for f in funcs: 
                                    f(content)
                            else:
                                continue
                    else:
                        continue
                #else:
                for _event, funcs in self.event_callbacks.items():
                    if _event == "all":
                        for f in funcs: 
                            f(content)
                    elif _event == event:
                        for f in funcs:
                            f(content)
                    else:
                        continue
            
        
        
