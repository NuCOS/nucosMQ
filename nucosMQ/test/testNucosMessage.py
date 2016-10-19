from __future__ import print_function

import unittest, time
import sys
sys.path.append('../../')


from nucosMQ import unicoding
from nucosMQ import version
import nucosMQ
print(nucosMQ.__file__)
print("VERSION: %s"%version)

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
    try:
        import xmlrunner
        xml = True
    except:
        xml = False

    if xml:        
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    else:
        unittest.main()
