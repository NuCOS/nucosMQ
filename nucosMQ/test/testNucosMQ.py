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

class UTestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = NucosClient(socketIP, socketPort, uid="testuser", on_challenge=on_challenge)
        cls.server = NucosServer(socketIP, socketPort, do_auth=Auth, single_server=False)
        cls.server.start()
        
                                
    def setUp(self):
        #self.client.prepare_auth( "testuser", on_challenge)
        self.client.start()
        
                
    def tearDown(self):
        global res
        res = []
        self.client.close()

    ## Test-Cases
    #def test_server_close(self):
    #    time.sleep(0.5)
    #    self.server.close()
    #    result = self.client.ping()
    #    self.assertFalse(result)
        
    def test_server_reinitialize(self):
        time.sleep(0.5)
        self.server.close()
        #self.server.reinitialize()
        self.server.start()
        self.client.start()
        result = self.client.ping()
        self.assertTrue(result)
        
    def test_client_close(self):
        pass
        
    def test_client_send(self):
        time.sleep(1.5)
        self.client.send("test-event", "a"*971) #test case for exactly 1024 length message
        #result = self.client.ping() #blocking until true or false
        #self.assertTrue(result)
        #self.client.close()
        
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
        self.server.send_room("testuser", "test-event alpha", msg)
        while True:
            time.sleep(0.1)
            try:
                result = res[0]
                break
            except:
                pass
        self.assertEqual(msg, result)

        
if __name__ == '__main__':
    import xmlrunner
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    #unittest.main()
