from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')
import random


socketIP = "127.0.0.1"
socketPort = 4000

from nucosMQ import NucosServer, NucosClientUDP


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


class UTestLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_udp = NucosServer("127.0.0.1",4000,udp=True)
        cls.client_udp = NucosClientUDP("127.0.0.1",4000)
        cls.server_udp.start()
                                
    def setUp(self):
        self.client_udp.start()
        time.sleep(0.2)
        
    def tearDown(self):
        global res
        #time.sleep(0.5)
        #self.server_udp.close()
        self.client_udp.close()
        time.sleep(0.5)
        res = []

    ## Test-Cases
    def test_udp_simple(self):
        self.client_udp.send("test", "hallo")
        

    def test_link_event_1(self):
        global res
        self.server_udp.add_event_callback("test-alpha", alpha)
        msg = "hallo1"
        self.client_udp.send("test-alpha",msg)
        time.sleep(0.5) #time for callback
        self.assertEqual(msg, res[0])
        

    
    
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
