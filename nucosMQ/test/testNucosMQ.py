from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')
import random


socketIP = "127.0.0.1"
socketPort = 4000

from nucosMQ import NucosClient
from nucosMQ import NucosServer

from nucosMQ import logger as globalLogger

res = []

class Auth():
    logger = globalLogger
    def auth_final(self, uid, signature, challenge):
        #print("TEST signature",uid, signature)
        allowed = signature == "1234"
        if not allowed:
            #logger.log("auth failed, disconnect")
            return False
        else:
            #logger.log("auth success, connect")
            return True
    def auth_challenge(self, uid):
        return "1234"
    
def alpha(x):
    global res
    res.append(x)

def on_challenge(x):
    return "1234"

def weather_callback(x):
    global res
    res.append(("weather-callback",x))

class UTestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = NucosClient(socketIP, socketPort, uid="testuser", on_challenge=on_challenge)
        cls.server = NucosServer(socketIP, socketPort, do_auth=Auth, single_server=False)
        cls.server.start()
        
                                
    def setUp(self):
        #self.client.prepare_auth( "testuser", on_challenge)
        self.client.start()
        time.sleep(0.5)
        
    def tearDown(self):
        global res
        res = []
        time.sleep(0.5)
        self.client.close()
        
    def test_server_reinitialize(self):
        self.server.close()
        time.sleep(0.5)
        self.server.start()
        self.client.start()
        result = self.client.ping()
        self.assertTrue(result)
        
    ##def test_timeout_ping(self):
    #    self.client.ping()
    #    time.sleep(12.0)
        #self.server.close()
        #time.sleep(10.0)
        
        
    def test_client_send(self):
        self.client.send("test-event", "a"*971) #test case for exactly 1024 length message
        #result = self.client.ping() #blocking until true or false
        #self.assertTrue(result)
        #self.client.close()
        
    def test_join_room(self):
        self.client.subscripe("weather")
        time.sleep(0.5) #needs to process the subcribe (maybe put the sleep time inside a specific subscribe call?)
        self.client.add_event_callback("today", weather_callback)
        self.server.publish("weather", "today", "sunny")
        while True:
            time.sleep(0.1)
            try:
                result = res[0]
                break
            except:
                pass
        self.assertEqual(("weather-callback",u"sunny"),result)
            
    def test_room_callback(self):
        self.client.subscripe("weather")
        time.sleep(0.5)
        self.client.add_room_callback("weather", weather_callback)
        self.server.publish("weather", "today", "sunny")
        while True:
            time.sleep(0.1)
            try:
                result = res[0]
                break
            except:
                pass
        self.assertEqual(("weather-callback",u"sunny"),result)
            
    def test_10_clients(self):
        c = []
        for n in range(10):
            z = str(random.random())
            cli = NucosClient(socketIP, socketPort, uid=z, on_challenge=on_challenge)
            
            #cli.prepare_auth( z, on_challenge)
            cli.start()
            c.append(cli)
        for cli in c:
            cli.send("test-event", "test-content")
        for cli in c:
            cli.close()
        
    def test_client_event(self):
        global res
        self.server.add_event_callback("test-event alpha", alpha)
        msg = "hello alpha"
        self.client.send("test-event alpha","hello alpha")
        #need time to get the callback done
        while True:
            time.sleep(0.1)
            try:
                result = res[0]
                break
            except:
                pass
        self.assertEqual(msg, result)
        
    def test_server_event(self):
        global res
        self.client.add_event_callback("test-event alpha", alpha)
        msg = "hello alpha client"
        self.server.publish("testuser", "test-event alpha", msg)
        while True:
            time.sleep(0.1)
            try:
                result = res[0]
                break
            except:
                pass
        self.assertEqual(msg, result)

        
if __name__ == '__main__':
    try:
        import xmlrunner
        xml = True
    except:
        xml = False

    if xml:        
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    else:
        unittest.main()
