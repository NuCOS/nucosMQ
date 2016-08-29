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
from inspect import isfunction
from collections import defaultdict

from .nucosLogger import Logger
from .nucosMessage import NucosIncomingMessage, NucosOutgoingMessage, SocketArray, EOM

logger = Logger('nucosServer')
logger.format(["clientip","user"], '[%(asctime)-15s] %(name)-8s %(levelname)-7s %(clientip)s %(user)s -- %(message)s')
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
TIMEOUT = 5.0
palace = defaultdict(list)

queue = queue.Queue()

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
    try:
        connection_sid.pop(addr)
    except:
        pass
    
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
    def handle(self):
        global AUTH
        conn = self.request
        conn.settimeout(TIMEOUT) #longest possible open connection without any message
        addr = self.client_address
        logger.log(msg= 'Incoming connection', clientip=addr)
        connection_sid.update({addr:conn})     #append the socket connection
        if AUTH:
            t = Thread(target=self.authenticate, args=(addr,conn))
            t.daemon = True
            t.start()
        fullData = SocketArray()
        while True:
            try:
                receivedData = SocketArray(conn.recv(1024))
            except socket.timeout:
                logger.log(lvl="WARNING", msg="server socket timeout")
                receivedData = receivedData.empty()
            except socket.error, ex:
                logger.log(lvl="WARNING", msg="server socket error %s"%ex)
                receivedData = receivedData.empty()
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
                if addr not in connection_auth_addr.keys(): #only for not authenticated clients put the data in the wait-stack
                    answer_stack[conn].append(fullData)
                if ON_CLIENTEVENT:
                    ON_CLIENTEVENT(addr, fullData)
                fullData = SocketArray()
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
    def __init__(self, IP_PORT):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IP_PORT = IP_PORT
    def serve_forever(self):
        self.s.bind(self.IP_PORT)
        self.s.listen(1)
        (conn, addr) = self.s.accept()
        logger.log(msg= 'Incoming connection (single-server)', clientip=addr)
        connection_sid.update({addr:conn})     #append the socket connection
        if AUTH:
            t = Thread(target=self.authenticate, args=(addr,conn))
            t.daemon = True
            t.start()
        while True:
            try:
                receivedData = conn.recv(1024)
            except socket.timeout:
                logger.log(lvl="WARNING", msg="server socket timeout")
                receivedData = ""
            except socket.error, ex:
                logger.log(lvl="WARNING", msg="server socket error %s"%ex)
                receivedData = ""
            if not queue.empty():
                msg = queue.get()
            else:
                msg = ""
            if msg=="kill-server":
                logger.log(lvl="DEBUG", msg="single server killed")
                break
            logger.log(lvl="DEBUG", msg="received package of length %i" % len(receivedData))
            logger.log(lvl="DEBUG", msg="payload: %s"%receivedData)
            if addr not in connection_auth_addr.keys(): #only for not authenticated clients put the data in the wait-stack
                answer_stack[conn].append(receivedData)
            if ON_CLIENTEVENT:
                ON_CLIENTEVENT(addr, receivedData)
            if not receivedData:  #server should stop automatically if no client is in any more:
                if addr in connection_sid.keys():
                    cleanup(addr, conn, close=True)
                    logger.log(lvl="DEBUG", msg="stop single-server now")
                    break
            #self.s.close()

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
    """
    
    def __init__(self,IP,PORT, do_auth=None, single_server=False, timeout=5.0):
        self.logger = logger
        self.auth_final = None
        self.IP = IP
        self.PORT = PORT
        global AUTH, ON_CLIENTEVENT
        #addr = (IP,PORT)
        if isfunction(do_auth):
            self.auth_final = do_auth
            AUTH = self.auth_protocoll
        self.single_server = single_server
        if not single_server:
            self.srv = ThreadingTCPServer((IP, PORT), ServerHandler)
        else:
            self.srv = SingleConnectionServer((IP,PORT))
        ON_CLIENTEVENT = lambda u,x: self.on_clientEvent(u,x)
        TIMEOUT = timeout
        self.auth_status = {}
        
    def reinitialize(self):
        """
        re-initialize a killed server
        """
        self.logger.log(lvl="DEBUG", msg="reinitialize the server")
        if not self.single_server:
            self.srv = ThreadingTCPServer((self.IP, self.PORT), ServerHandler)
        else:
            self.srv = SingleConnectionServer((self.IP,self.PORT))
        
    def start(self):
        """
        start a non-blocking server
        """
        self.logger.log(lvl="INFO", msg="try to start server")
        t = Thread(target=self.srv.serve_forever)
        t.daemon = True
        t.start()
        
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
        self.queue.put_topic("ping","wait")
        msg = self.queue.get_topic("pong", timeout=5.0)
        if msg == "done":
            return True
        else:
            return False
        
    def send(self, event, content):
        """
        send a message to all connected clients
        """
        data = { "event": event, "content": content }
        message = NucosOutgoingMessage(data)
        
        payload,error = message.payload()
        
        if error:
            logerror = "outgoing msg error e: %s pl: %s type(pl): %s"%(error,payload,type(payload))
            self.logger.log(lvl="ERROR",msg=logerror)
            raise Exception(logerror)    
        
        if connection_sid:
            for addr, conn in connection_sid.items():
                conn.send(payload)
    
    def join_room(self, room, uid):
        """
        append a user to a room
        """
        palace[room].append(uid)
        
    def on_clientEvent(self, addr, payload):
        """
        for every client event this function is called
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
            event = msg["event"]
            content = msg["content"]
            logger.log(lvl="INFO", msg="incoming clientEvent: %s | %s"%(event,content), user=uid)
            if event == "shutdown":
                #self.send_room(uid, "shutdown", "confirmed")
                self.send_via_conn(connection_sid[addr], "shutdown", "confirmed")
                #queue.put("kill-auth")
                #on_shutdown.append(addr)
            elif event == "ping":
                self.send_via_conn(connection_sid[addr], "pong", "")
        
    def force_close(self):
        queue.put("kill-server")
        logger.log(lvl="WARNING", msg="server is forced to shut-down now")
        cosid = copy.copy(connection_sid)
        for addr,conn in cosid.items():
            #gracefully:
            self.send_via_conn(conn, "shutdown", "now")
            time.sleep(0.1)
            cleanup(addr, conn)
        self.srv.shutdown()
        self.srv.server_close()
        
    def send_room(self, room, event, content):
        """
        send a message to all clients in a room
        """
        logger.log(lvl="DEBUG", msg="send in room: %s | %s | %s"%(room,event,content))
        data = { "event": event, "content": content }
        message = NucosOutgoingMessage(data)
        
        payload,error= message.payload()
        if error:
            logerror = "outgoing msg error %s"%error
            self.logger.log(lvl="ERROR",msg=logerror)
            raise Exception(logerror)    
        for _room, uids  in palace.items():
            if _room == room: 
                for uid in uids:
                    addr = connection_auth_uid[uid]
                    conn = connection_sid[addr]
                    conn.send(payload)
                    logger.log(lvl="DEBUG", msg="send in room: %s | %s | %s"%(room,event,content))
            
    def send_via_conn(self, conn, event, content):
        """
        send a message to a client for given connection data
        """
        data = { "event": event, "content": content }
        message = NucosOutgoingMessage(data)
        payload,error = message.payload()
        if error:
            logerror = "outgoing msg error e: %s pl: %s type(pl): %s"%(error,payload,type(payload))
            logger.log(lvl="ERROR",msg=logerror)
            raise Exception(logerror)
        conn.send(payload)
        
        logger.log(lvl="DEBUG", msg="send via conn: %s | %s | %s"%(conn, event,content))
        
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
            #time.sleep(0.01)
        
    def auth_protocoll(self, addr, conn):
        """
        definition of the authentification protocoll: start_auth, challenge_auth, auth_final
        """
        global SHUTDOWN
        ############################################################
        # step 1: start_auth event
        self.send_via_conn(conn, "start_auth", "")
        data = self.wait_for_answer(conn)
        if data:
            uid = data["content"]
        else:
            cleanup(addr,conn)
            return
        ############################################################
        # step 2: hand out the challenge and receive signature
        self.send_via_conn(conn, "challenge_auth", "1234") #TODO introduce an AUTH object with challenge creation
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
        if self.auth_final(uid, signature):
            connection_auth_uid.update({uid:addr})
            connection_auth_addr.update({addr:uid})
            palace.update({uid:[uid]}) #create a room with the uid as name
            self.send_via_conn(conn, "auth_final", "success")
        else:
            #print(dir(conn))
            self.send_via_conn(conn, "auth_final", "failed")
            cleanup(addr,conn)
            #self.srv.server_close()
            #self.srv.shutdown()
