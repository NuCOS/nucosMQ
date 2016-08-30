import time
from .nucos23 import ispython3
if ispython3:
    import queue
else:
    import Queue as queue

from threading import Thread
    
class NucosQueue():
    """
    a generalized communication queue for threads, works with dictionaries of the form {topic: text}, all other queue elements are recycled in the queue
    """
    def __init__(self):
        #super(NucosQueue, self).__init__()
        self.queue = queue.Queue()
        self.topic_buffer = []
        self.cycle_buffer = []
        
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
                if type(msg) is dict:
                    #print "keys:",msg.keys()
                    if topic in msg.keys():
                        out = msg[topic]
                        return out
                    else:
                        self.topic_buffer.append(msg)
                else:
                    self.cycle_buffer.append(msg)
            else:
                if self.topic_buffer:
                    keys = [list(x.keys())[0] for x in self.topic_buffer]
                    if topic in keys:
                        out = self.topic_buffer.pop(keys.index(topic))[topic]
                        break
                time.sleep(0.2)
                tau = time.time() - start_time
                if tau > timeout:
                    break
        return out
    
    def _feed_queue(self, timeout=2.0):
        """
        make sure no other queue item is lost, it is feed in the queue back again
        """
        import time #due to some threading import bug
        start_time = time.time()
        while True:
            time.sleep(0.1)  #cycle in time
            if self.cycle_buffer:
                self.queue.put(self.cycle_buffer.pop(0))
            tau = time.time() - start_time
            if tau > timeout:
                break
            
        
    def put_topic(self, topic, text):
        """
        put the kind of queue messages which are further processed by this class
        """
        self.queue.put({topic:text})
        
    def put(self, item):
        self.queue.put(item)
        
    def get(self):
        return self.queue.get()
    
    def empty(self):
        return self.queue.empty()