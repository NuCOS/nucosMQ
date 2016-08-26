import threading
import Queue

active_queues = []

class Worker(threading.Thread):
    def __init__(self, **kwargs):
        #super(Worker, self).__init__(**kwargs)
        self._target = kwargs["target"]
        self._args = kwargs(args)
        threading.Thread.__init__(self)
        
        self.mailbox = Queue.Queue()
        active_queues.append(self.mailbox)

    def run(self):
        self._target(*self._args)
        while True:
            data = self.mailbox.get()
            if data == 'shutdown':
                print self, 'shutting down'
                return
            print self, 'received a message:', data

    def stop(self):
        active_queues.remove(self.mailbox)
        self.mailbox.put("shutdown")
        self.join()