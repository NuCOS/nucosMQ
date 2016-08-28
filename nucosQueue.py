import time
from .nucos23 import ispython3
if ispython3:
    import queue
else:
    import Queue as queue

from threading import Thread
    
class NucosQueue():
    """
    a generalized communication queue for all threads, works with dictionaries of the form {topic: text}
    """
    def __init__(self):
        #super(NucosQueue, self).__init__()
        self.queue = queue.Queue()
        self._buffer = []
        
    def get_topic(self, topic, timeout=2.0): #, block=False, timeout=10.0):
        """
        get topic msg
        """
        t = Thread(target=self._feed_queue)
        t.deamon = True
        t.start()
        out = str()
        start_time = time.time()
        while True:
            if not self.queue.empty():
                msg = self.queue.get()
                #print msg, self._buffer
                if type(msg) is dict:
                    #print "keys:",msg.keys()
                    if topic in msg.keys():
                        out = msg[topic]
                        return out
                    else:
                        self._buffer.append(msg)
                else:
                    self._buffer.append(msg)
                #print msg, self._buffer
            else:
                time.sleep(0.2)
                tau = time.time() - start_time
                if tau > timeout:
                    break
        return out
    
    def _feed_queue(self, timeout=5.0):
        start_time = time.time()
        while True:
            time.sleep(0.1)  #cycle in time
            if self._buffer:
                self.queue.put(self._buffer.pop(0))
            tau = time.time() - start_time
            if tau > timeout:
                break
            
        
    def put_topic(self, topic, text):
        self.queue.put({topic:text})
        
    def put(self, item):
        self.queue.put(item)
        
    def get(self):
        return self.queue.get()
    
    def empty(self):
        return self.queue.empty()