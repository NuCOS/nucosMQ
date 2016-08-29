from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')
import random


socketIP = "127.0.0.1"
socketPort = 4000

from nucosMQ import NucosClient
from nucosMQ import NucosServer

def auth(uid, signature):
    print("TEST signature",uid, signature)
    allowed = signature == "1234"
    if not allowed:
        #logger.log("auth failed, disconnect")
        return False
    else:
        #logger.log("auth success, connect")
        return True

def on_challenge(x):
    return "1234"

class UTestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = NucosClient(socketIP, socketPort)
        cls.server = NucosServer(socketIP, socketPort, do_auth=auth, single_server=False)
        cls.server.start()
                                
    def setUp(self):
        self.client.prepare_auth( "testuser", on_challenge)
        self.client.start()
                
    def tearDown(self):
        time.sleep(1.0)

    ## Test-Cases
    def test_server_force_down(self):
        time.sleep(1.0)
        self.server.force_close()
        result = self.client.ping()
        self.assertFalse(result)
        self.server.reinitialize()
        self.server.start()
        
    def test_client_close(self):
        time.sleep(1.0)
        self.client.close()
        
    def test_client_send(self):
        self.client.send("test-event", "a"*971) #test case for exactly 1024 length message
        result = self.client.ping() #blocking until true or false
        self.assertTrue(result)
        self.client.close()
        
    def test_10_clients(self):
        c = []
        for n in range(10):
            cli = NucosClient(socketIP, socketPort)
            z = str(random.random())
            cli.prepare_auth( z, on_challenge)
            cli.start()
            c.append(cli)
        #for cli in c:
        #       cli.send("test-event", "test-content")
        for cli in c:
            cli.close()
            
            
        
    
if __name__ == '__main__':
    unittest.main()