from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')


from nucosMQ import unicoding

class UTestMessage(unittest.TestCase):
    
    def tearDown(self):
        pass
    def setUp(self):
        pass
    
    def test_unicoding(self):
        a = b"abc"
        b = unicoding(a)
        self.assertEqual(type(b), type(u''))
        
        
        
        
    
if __name__ == '__main__':
    import xmlrunner
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    #unittest.main()
