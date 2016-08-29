from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')
import random


socketIP = "127.0.0.1"
socketPort = 4000

from nucosMQ import NucosLink


res = []

def auth(uid, signature):
    #print("TEST signature",uid, signature)
    allowed = signature == "1234"
    if not allowed:
        #logger.log("auth failed, disconnect")
        return False
    else:
        #logger.log("auth success, connect")
        return True
    
def alpha(x):
    global res
    res.append(x)

def on_challenge(x):
    return "1234"

class UTestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.link_1 = NucosLink()
        cls.link_2 = NucosLink()
        #cls.server.start()
                                
    def setUp(self):
        pass
        #self.client.prepare_auth( "testuser", on_challenge)
        #self.client.start()
                
    def tearDown(self):
        pass
        #time.sleep(2.0)
        #self.client.close()

    ## Test-Cases
    def test_link_simple(self):
        self.link_1.bind("127.0.0.1",4000)
        self.link_2.connect("127.0.0.1", 4000)
        self.link_1.send("test", "hallo")
        time.sleep(2.0)
        #self.link_2.bind("127.0.0.1",4000)
        self.link_1.close()
        self.link_2.close()
        
    def test_link_event(self):
        global res
        self.link_1.bind("127.0.0.1",4000)
        self.link_2.connect("127.0.0.1", 4000)
        self.link_1.add_event_callback("test-alpha", alpha)
        self.link_2.send("test", "hallo")

        msg = "hallo"
        self.link_2.send("test-alpha",msg)
        time.sleep(0.4) #time for callback
        self.assertEqual(msg, res[0])
        self.link_1.close()
        self.link_2.close()
        
    def test_ping_1(self):
        global res
        self.link_1.bind("127.0.0.1",4000)
        self.link_2.connect("127.0.0.1", 4000)
        self.link_1.ping()
        time.sleep(0.4)
        #self.link_2.bind("127.0.0.1",4000)
        self.link_1.close()
        self.link_2.close()
        
    def test_ping_2(self):
        global res
        self.link_1.bind("127.0.0.1",4000)
        self.link_2.connect("127.0.0.1", 4000)
        self.link_2.ping()
        time.sleep(0.4)
        #self.link_2.bind("127.0.0.1",4000)
        self.link_1.close()
        self.link_2.close()
        

    
if __name__ == '__main__':
    unittest.main()