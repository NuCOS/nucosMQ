from __future__ import print_function
from __future__ import absolute_import


from .nucos23 import ispython3
if ispython3:
    import socketserver
    import queue
    
else:
    import SocketServer as socketserver
    import Queue as queue

from threading import Thread

import time
import copy

import socket
from inspect import isclass, ismethod
from collections import defaultdict

from .nucosLogger import Logger
from .nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, SocketArray, EOM, unicoding

logger = Logger('nucosServer', ["clientip","user"])
logger.format('[%(asctime)-15s] %(name)-8s %(levelname)-7s %(clientip)s %(user)s -- %(message)s')
logger.level("DEBUG")

connection_sid = {}
connection_auth_uid = {}
connection_auth_addr = {}

#palace = {}

on_disconnect = [] #disconnect-handler
on_connect = []    #connect-handler
on_receive = []    #receive-handler
on_shutdown = []
AUTH = None
ON_CLIENTEVENT = None
SERVE_FOREVER = True
SHUTDOWN = False
TIMEOUT = 300.0
palace = defaultdict(list)

queue = queue.Queue()
from .nucosQueue import NucosQueue

t_auth = None

def cleanup(addr, conn, close=True):
    """
    cleans all traces of connection data in the globals
    close the socket if close-flag is True, otherwise not
    """
    uid = ""
    if addr in connection_auth_addr.keys():
        uid = connection_auth_addr[addr]
    logger.log(msg= 'Cleanup', clientip=addr, user=uid)
    if close:
        conn.close()
    
    connection_sid.pop(addr)
    #except:
    #    pass
    
    try:
        palace.pop(uid)
    except:
        pass
    try:
        connection_auth_addr.pop(addr)
        connection_auth_uid.pop(uid)
    except:
        pass
    #TODO remove singular rooms
    #print(connection_sid, connection_auth, palace)
    return 
        
answer_stack = defaultdict(list)

class ServerHandler(socketserver.BaseRequestHandler):
    """
    The server handler class 
    """
    no_auth = False
    def handle(self):
        global AUTH, t_auth
        conn = self.request
        conn.settimeout(TIMEOUT) #longest possible open connection without any message
        addr = self.client_address
        logger.log(msg= 'Incoming connection', clientip=addr)
        connection_sid.update({addr:conn})     #append the socket connection
        if AUTH:
            t_auth = Thread(target=self.authenticate, args=(addr,conn))
            t_auth.daemon = True
            t_auth.start()
        else:
            self.no_auth = True
        fullData = SocketArray()
        while True:
            try:
                receivedData = SocketArray(conn.recv(1024))
            except socket.timeout:
                logger.log(lvl="WARNING", msg="server socket timeout")
                receivedData = SocketArray.empty()
            except socket.error as ex:
                logger.log(lvl="WARNING", msg="server socket error %s"%ex)
                receivedData = SocketArray.empty()
                break
            ####
            # kill server logic:
            if not queue.empty():   
                msg = queue.get()
            else:
                msg = ""
            if msg=="kill-server":
                logger.log(lvl="DEBUG", msg="connection killed")
                if connection_sid: #kill all other threads in subsequence
                    queue.put("kill-server")
                break
            ####
            if receivedData:
                fullData = fullData.ext(receivedData)
                if len(receivedData) == 1024:
                    logger.log(lvl="DEBUG", msg="max length 1024 %s"%receivedData)
                    if not fullData.endswith(EOM):
                        logger.log(lvl="DEBUG", msg="continue listening")
                        continue
                logger.log(lvl="DEBUG", msg="received package of length %i" % len(receivedData))
                logger.log(lvl="DEBUG", msg="payload: %s"%receivedData)
                if addr not in connection_auth_addr.keys() and not self.no_auth: #only for not authenticated clients put the data in the wait-stack
                    answer_stack[conn].append(fullData)
                    fullData = SocketArray()
                    continue
                if ON_CLIENTEVENT:
                    ON_CLIENTEVENT(addr, fullData)
                    fullData = SocketArray()
                    continue
            else:
                if addr in connection_sid.keys():
                    cleanup(addr, conn, close=True) #close or not close ???? why ?
                    logger.log(lvl="DEBUG", msg="stop this connection now")
                    break
            
                
    def authenticate(self, addr, conn):
        logger.log(msg='Start auth-process')
        AUTH(addr, conn)
        return


class ThreadingTCPServer(socketserver.ThreadingTCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

class SingleConnectionServer():
    """
    A single connection Server: accepts only one connection
    """
    def __init__(self, IP_PORT, udp=False):
        if udp:
            socktype = socket.SOCK_DGRAM
        else:
            socktype = socket.SOCK_STREAM
        self.socket = socket.socket(socket.AF_INET, socktype)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.IP_PORT = IP_PORT
        self.no_auth = False
        self.udp = udp
        
    def serve_forever(self):
        global AUTH, ON_CLIENTEVENT
        try:
            self.socket.bind(self.IP_PORT)
        except socket.error as ex:
            logger.log(lvl="DEBUG", msg="single server socket exception %s"%ex)
            self.socket.close()
            raise Exception
        if not self.udp:
            self.socket.listen(1)
            (conn, addr) = self.socket.accept()
            logger.log(msg= 'Incoming connection (single-server)', clientip=addr)
            connection_sid.update({addr:conn})     #append the socket connection
        if AUTH:
            t = Thread(target=self.authenticate, args=(addr,conn))
            t.daemon = True
            t.start()
        else:
            self.no_auth = True
        fullData = SocketArray()
        logger.log(lvl="DEBUG", msg="start listening")
        while True:
            try:
                if not self.udp:
                    receivedData = SocketArray(conn.recv(1024))
                else:
                    receivedData = self.socket.recvfrom(1024)
            except socket.timeout:
                logger.log(lvl="WARNING", msg="server socket timeout")
                receivedData = SocketArray.empty()
            except socket.error as ex:
                logger.log(lvl="WARNING", msg="server socket error %s"%ex)
                receivedData = SocketArray.empty()
                raise Exception
            if not queue.empty():
                msg = queue.get()
            else:
                msg = ""
            if msg=="kill-server":
                logger.log(lvl="DEBUG", msg="single server killed")
                break
            if receivedData:
                if self.udp:
                    receivedData = receivedData[0]
                    addr = receivedData[1]                   
                    logger.log(lvl="DEBUG", msg="message received %s"%receivedData)
                    
                fullData = fullData.ext(receivedData)
                if len(receivedData) == 1024:
                    logger.log(lvl="DEBUG", msg="max length 1024 %s"%receivedData)
                    if not fullData.endswith(EOM):
                        logger.log(lvl="DEBUG", msg="continue listening")
                        continue
                logger.log(lvl="DEBUG", msg="received package of length %i" % len(receivedData))
                logger.log(lvl="DEBUG", msg="payload: %s"%receivedData)
                if addr not in connection_auth_addr.keys() and not self.no_auth: #only for not authenticated clients put the data in the wait-stack
                    answer_stack[conn].append(receivedData)
                    fullData = SocketArray()
                    continue
                if ON_CLIENTEVENT:
                    ON_CLIENTEVENT(addr, fullData)
                    fullData = SocketArray()
                    continue
            else:
                cleanup(addr, conn, close=True)
                logger.log(lvl="DEBUG", msg="stop single-server now")
                break


    def authenticate(self, addr, conn):
        logger.log(msg='Start auth-process')
        AUTH(addr, conn)
        return
    
    def shutdown(self):
        pass
    def server_close(self):
        pass
    

class NucosServer():
    """
    base NuCOS socket class on server side
    
    implements protocol on top of tcp/ip socket
    
    accepts either one or many clients (depends on single_server flag) and starts them in individual threads.
    
    do_auth is a function handler which accepts 3 arguments: uid, signature, challenge
    """
    
    def __init__(self,IP,PORT, do_auth=None, single_server=False, timeout=300.0, udp=False):
        global AUTH, ON_CLIENTEVENT
        self.logger = logger
        self.auth_final = None
        self.IP = IP
        self.PORT = PORT
        self.in_auth_process = []
        self.send_later = []
        self.queue = NucosQueue()
        self.shutdown_process = []
        self.udp = udp
        
        if isclass(do_auth):
            AUTH = self._auth_protocoll
            self.do_auth_obj = do_auth()
            if ismethod(self.do_auth_obj.auth_final):
                self.auth_final = self.do_auth_obj.auth_final
            else:
                raise Exception("auth class has no auth_final")
            if ismethod(self.do_auth_obj.auth_challenge):
                self.auth_challenge = self.do_auth_obj.auth_challenge
            else:
                raise Exception("auth class has no auth_challenge")
        elif do_auth is None:
            self.logger.log(lvl="INFO", msg="no auth selected")
        else:
            raise Exception("only class as do_auth accepted")
        self.single_server = single_server
        if udp:
            self.single_server = True
        if not self.single_server:
            self.srv = ThreadingTCPServer((IP, PORT), ServerHandler)
        else:
            self.srv = SingleConnectionServer((IP,PORT), udp=self.udp)
        ON_CLIENTEVENT = lambda u,x: self._on_clientEvent(u,x)
        TIMEOUT = timeout
        self.auth_status = {}
        self.event_callbacks = defaultdict(list)
        
    def getsockname(self):
        return self.srv.socket.getsockname()

    def _reinitialize(self):
        """
        re-initialize a killed server
        """
        while not queue.empty():
            queue.get()
        self.auth_status = {}
        self.shutdown_process = []
        self.logger.log(lvl="DEBUG", msg="reinitialize the server")
        
        if not self.single_server:
            self.srv = ThreadingTCPServer((self.IP, self.PORT), ServerHandler)
        else:
            self.srv = SingleConnectionServer((self.IP,self.PORT))
        
    def start(self):
        """
        start a non-blocking server
        """
        self.logger.log(lvl="INFO", msg="... try to start server")
        t = Thread(target=self.srv.serve_forever)
        t.daemon = True
        t.start()
        time.sleep(0.2) #startup time for server
        
    def is_connected(self, conn):
        return conn in connection_sid.values()
        
    def ping(self, conn):
        """
        send a ping event and wait for a pong (blocking call, since it expects the answer right away)
        """
        start_time = time.time()
        while conn in self.in_auth_process:
            tau = time.time()-start_time
            time.sleep(0.1)
            if tau > self.ping_timeout:
                return False
        self.logger.log(lvl="INFO", msg="send a ping, expects a pong")
        self.send(conn, "ping", "")
        self.queue.put_topic("ping-server","wait")
        msg = self.queue.get_topic("pong-server", timeout=5.0)
        if msg == "done":
            return True
        else:
            return False
        
    def send(self, conn, event, content, room=''):
        """
        the send command for a given connection conn, all other send commands must call send to prevent auth-protocoll confusion
        """
        logger.log(lvl="DEBUG", msg="send via conn: %s | %s | %s"%(conn, event, content))
        if conn in self.in_auth_process:
            self.send_later.append((conn, event,content))
            self.logger.log(lvl="WARNING", msg="no send during auth: %s %s %s"%(conn, event,content))
            return True
        return self._send(conn, event, content, room)
        
    def _send(self, conn, event, content, room=''):
        """
        finalize the send process
        """
        if self.udp:
            return
        self.logger.log(lvl="DEBUG", msg="try to do _send: %s %s %s"%(conn, event,content))
        if not room:
            data = { "event":event, "content":content }
        else:
            data = { "event":event, "content":content, "room":room }
        message = NucosOutgoingMessage(data)
        payload,error = message.payload()
        if error:
            logerror = "outgoing msg error e: %s pl: %s type(pl): %s"%(error,payload,type(payload))
            self.logger.log(lvl="ERROR",msg=logerror)
            #raise Exception(logerror)
            return False
        try:
            conn.send(payload)
            return True
        except socket.error as ex:
            self.logger.log(lvl="ERROR",msg="socket error during send-process %s %s %s"%(ex, conn, connection_sid))
            return False
            
    def _flush(self):
        """
        send all pre-processed send commands during auth process
        """
        for conn,event,content in self.send_later:
            self.send(conn,event,content)
        self.send_later = []
        
    def send_all(self, event, content):
        """
        send a message to all connected clients
        """
        if connection_sid:
            for addr, conn in connection_sid.items():
                self.send(conn, event, content)
                
    def publish(self, room, event, content):
        """
        send a message to all clients in a room
        """
        #conn = self.get_conn(room)
        self.wait_for_auth()
        logger.log(lvl="DEBUG", msg="send in room: %s | %s | %s"%(room,event,content))
  
        for _room, uids  in palace.items():
            if _room == room: 
                for uid in uids:
                    addr = connection_auth_uid[uid]
                    conn = connection_sid[addr]
                    self.send(conn, event, content, room)
                        
    def join_room(self, room, uid):
        """
        append a user to a room, if uid is not anonymous and the desired room is not one of the other users (they should stay private)
        """
        if not uid=="anonymous" and not room in connection_auth_uid:
            logger.log(lvl="DEBUG", msg="user %s entered room %s"%(uid,room))
            palace[room].append(uid)
        
    def _on_clientEvent(self, addr, payload):
        """
        for every client event this function is called
        
        internal events:
        ----------------
        
        shutdown
        ping
        pong
        
        """
        if addr in connection_auth_addr.keys():
            uid = connection_auth_addr[addr]
        else:
            uid = "anonymous"
        incoming = NucosIncomingMessage(payload)
        msgs, error = incoming.msgs()
        if error:
            logger.log(lvl="WARNING", msg="error in incoming message: %s"%error)
        for msg in msgs:
            event = unicoding(msg["event"])
            content = unicoding(msg["content"])
            if 'room' in msg.keys():
                room = msg["room"]
            else:
                room = ''
            logger.log(lvl="INFO", msg="incoming clientEvent: %s | %s | %s"%(event,content,room), user=uid)
            if self.udp:
                for _event, funcs in self.event_callbacks.items():
                    if _event == "all":
                        for f in funcs: 
                            f(content)
                    if _event == event:
                        for f in funcs:
                            f(content)
                    else:
                        continue
                return
            if room:
                self.publish(room,event,content)
                return
            if event == "shutdown":
                self.send(connection_sid[addr], "shutdown", "confirmed")
                self.shutdown_process.append(uid)
            elif event == "ping":
                self.send(connection_sid[addr], "pong", "")
            elif event == "pong":
                msg = self.queue.get_topic("ping-server", timeout=10.0)
                if not msg == "wait":
                    self.logger.log(lvl="ERROR", msg="pong received no ping send %s"%msg)
                self.logger.log(lvl="INFO", msg="pong received")
                self.queue.put_topic("pong-server", "done")
            elif event == "subscripe":
                self.join_room(content, uid)
            else:
                for _event, funcs in self.event_callbacks.items():
                    if _event == "all":
                        for f in funcs: 
                            f(content)
                    if _event == event:
                        for f in funcs:
                            f(content)
                    else:
                        continue
            
    def close(self):
        queue.put("kill-server")
        logger.log(lvl="WARNING", msg="server is forced to shut-down now")
        cosid = copy.copy(connection_sid)
        for addr,conn in cosid.items():
            #gracefully:
            self.send(conn, "shutdown", "now")
            time.sleep(0.1)
            cleanup(addr, conn)
        self.srv.shutdown()
        self.srv.server_close()
        self._reinitialize()

                    
    def wait_for_auth(self):
        start_time = time.time()
        while True:
            if connection_auth_uid:
                return
            else:
                tau = time.time() - start_time
                if tau > 5:
                    return
                else:
                    time.sleep(0.1)
                
    def get_conn(self, uid):
        #uid = unicoding(uid)
        start_time = time.time()
        while True:
            if uid in self.shutdown_process:
                break
            #print(connection_sid, connection_auth_uid,uid)
            if uid in connection_auth_uid.keys():
                return connection_sid[connection_auth_uid[uid]]
            elif uid == "anonymous": #take the first which is connected
                if connection_sid:
                    #print (connection_sid)
                    return list(connection_sid.values())[0]
            else:
                tau = time.time() - start_time
                if tau > 5:
                    return None
                else:
                    time.sleep(0.1)

        
    def wait_for_answer(self, conn):
        """
        blocking call for waiting for a client answer, which is connected via conn
        """
        start_time = time.time()
        while True:
            tau = time.time()-start_time
            if tau > 1.0:
                logger.log(lvl="WARNING", msg="auth failed")
                return
            if answer_stack[conn]:
                payload = answer_stack[conn].pop(0)
                incoming = NucosIncomingMessage(payload)
                msgs, error = incoming.msgs()
                if error:
                    logger.log("incoming message error: %i"%error)
                    return None
                #logger.log("from wait-loop: %s"%(msgs,))
                if msgs:
                    return msgs[0]
                
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
        self.event_callbacks[unicoding(event)].append(delegate)
        
    def _auth_protocoll(self, addr, conn):
        """
        definition of the authentification protocoll: start_auth, challenge_auth, auth_final
        """
        global SHUTDOWN
        ############################################################
        # step 1: start_auth event
        self.in_auth_process.append(conn)
        self._send(conn, "start_auth", "")
        data = self.wait_for_answer(conn)
        if data:
            uid = data["content"]
        else:
            cleanup(addr,conn)
            return
        ############################################################
        # step 2: hand out the challenge and receive signature
        challenge = self.auth_challenge(uid=uid)
        self._send(conn, "challenge_auth", challenge) #TODO introduce an AUTH object with challenge creation
        data = self.wait_for_answer(conn) #TODO define timeout!!!
        if data:
            signature = data["content"]
            event = data["event"]
        else:
            cleanup(addr,conn)
            return
        if not event == "signature":
            cleanup(addr,conn)
            return
        #if queue.get() == "kill-auth":
        #    #print("kill-auth")
        #    cleanup(addr,conn)
        #    return
        ############################################################
        # step 3: check the signature and send a result to the client
        if self.auth_final(uid=uid, signature=signature, challenge=challenge):
            connection_auth_uid.update({uid:addr})
            connection_auth_addr.update({addr:uid})
            palace.update({uid:[uid]}) #create a room with the uid as name
            self._send(conn, "auth_final", "success")
            self.in_auth_process.remove(conn)
            self._flush()
        else:
            self._send(conn, "auth_final", "failed")
            self.in_auth_process.remove(conn)
            cleanup(addr,conn)
            #self.srv.server_close()
            #self.srv.shutdown()
