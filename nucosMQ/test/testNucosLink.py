from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')
import random


socketIP = "127.0.0.1"
socketPort = 4000

from nucosMQ import NucosLink
from nucosMQ import version
import nucosMQ
print(nucosMQ.__file__)
print("VERSION: %s"%version)

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

class UTestLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.link_1 = NucosLink()
        cls.link_2 = NucosLink()
        #cls.server.start()
                                
    def setUp(self):
        self.link_1.bind("127.0.0.1",4000)
        self.link_2.connect("127.0.0.1", 4000)
        time.sleep(0.2)
        
    def tearDown(self):
        global res
        #time.sleep(0.5)
        self.link_2.close()
        self.link_1.close()
        time.sleep(0.5)
        res = []

    ## Test-Cases
    def test_link_simple(self):
        self.link_1.send("test", "hallo")
        answer = self.link_1.is_connected()
        self.assertTrue(answer)
        answer = self.link_2.is_connected()
        self.assertTrue(answer)

    def test_link_event_1(self):
        global res
        self.link_2.add_event_callback("test-alpha", alpha)
        self.link_1.send("test", "hallo")
        msg = "hallo1"
        self.link_1.send("test-alpha",msg)
        time.sleep(0.5) #time for callback
        self.assertEqual(msg, res[0])
        
    def test_link_event_2(self):
        global res
        self.link_1.add_event_callback("test-alpha", alpha)
        self.link_2.send("test", "hallo")
        msg = "hallo2"
        self.link_2.send("test-alpha",msg)
        time.sleep(0.5) #time for callback
        self.assertEqual(msg, res[0])
 
    def test_ping_1(self):
        res = self.link_1.ping()
        self.assertTrue(res)

    def test_ping_2(self):
        global res
        res = self.link_2.ping()
        self.assertTrue(res)

    def test_rebind_1(self):
        res = self.link_2.bind("127.0.0.1",4000)
        self.assertFalse(res)
        
    def test_rebind_2(self):
        res = self.link_1.bind("127.0.0.1",4000)
        self.assertFalse(res)
        
    def test_reconnect_1(self):
        res = self.link_2.connect("127.0.0.1",4000)
        self.assertFalse(res)
    
    def test_reconnect_2(self):
        res = self.link_1.connect("127.0.0.1",4000)
        self.assertFalse(res)
        
    def test_close_11(self):
        self.link_1.close()
        time.sleep(0.5)
        res = self.link_1.send("test", "hallo")
        self.assertFalse(res)
        answer = self.link_2.is_connected()
        self.assertFalse(answer)
        
    def test_close_12(self):
        self.link_1.close()
        time.sleep(0.5)
        res = self.link_2.send("test", "hallo")
        self.assertFalse(res)
        answer = self.link_1.is_connected()
        self.assertFalse(answer)
        
    def test_close_22(self):
        self.link_2.close()
        res = self.link_2.send("test", "hallo")
        self.assertFalse(res)
        answer = self.link_2.is_connected()
        self.assertFalse(answer)
        
    def test_close_21(self):
        self.link_2.close()
        time.sleep(0.5)
        res = self.link_1.send("test", "hallo")
        self.assertFalse(res)
        answer = self.link_1.is_connected()
        self.assertFalse(answer)
    
    
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
