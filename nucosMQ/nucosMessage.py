from __future__ import unicode_literals
from __future__ import absolute_import

import json
from .nucos23 import ispython3
from .nucosLogger import Logger
if ispython3:
    EOM = b"_EOM_" #put a fancy message-limiter inside
else:
    EOM = "_EOM_"
    
NO_DICT_ERROR = 2
FORMAT_ERROR = 1

logger = Logger('nucosMessage', [])
logger.format('[%(asctime)-15s] %(name)-8s %(levelname)-7s -- %(message)s')
logger.level("INFO")

if ispython3:
    def unicoding(x):
        #print(type(x),x[0])
        if type(x) is bytearray:
            return x.decode()
        elif type(x) is bytes:
            return x.decode()
        elif type(x) is str:
            return x
        else:
            return x
            
    class SocketArray(bytearray):
        def __init__(self,*args):
            if args:
                if type(args[0]) is str:
                    arg = bytearray(args[0].encode())
                    super(SocketArray,self).__init__(arg)
                else:
                    super(SocketArray,self).__init__(*args)
            else:
                super(SocketArray,self).__init__()
                
        def ext(self,cdr):
            if type(cdr) is str:
                cdr = bytearray(cdr.encode())
            
            self.extend(cdr)
            return self
        
        @classmethod
        def empty(self):
            return SocketArray(b"")
        
else: 
        
    def unicoding(x):
        if type(x) is bytearray:
            return unicode(x) #better use decode here?
        elif type(x) is bytes:
            return unicode(x) #better use decode here?
        elif type(x) is str:
            x = x.decode()
            return x
        elif type(x) is unicode:
            return x
        else:
            return x
        
    class SocketArray(str):
        def __init__(self,*args):
            super(SocketArray,self).__init__(*args)
        def ext(self,cdr):
            return SocketArray("".join([self,cdr]))
        
        @classmethod
        def empty(self):
            return SocketArray("")
            

class NucosIncomingMessage():
    """
    simple incoming message protocol
    
    message contains an event and content
    """
    def __init__(self, payload):
        self.payload = payload
        if ispython3:
            self.payload = self.payload.decode()
        
    def msgs(self):
        error = 0
        
        msgs = self.payload.split(unicoding(EOM))
        out = []
        for msg in msgs[:-1]:
            try:
                dict_msg= json.loads(msg)["data"]
            except:
                error = NO_DICT_ERROR
                return out,error
            if not "event" in dict_msg.keys():
                error = FORMAT_ERROR
            if not "content" in dict_msg.keys():
                error = FORMAT_ERROR
            out.append(dict_msg)
        return unicoding(out), error # a list of dicts, one or maybe several
    
class NucosOutgoingMessage():
    """
    simple outgoing message protocol
    
    data values must be a primitive datatype or json pickable supported
    data is a well formed input if it is a dict and contains an event and content key.
    """
    def __init__(self, data):
        self.data = { "data": data }
    def payload(self):
        """
        
        """
        out = SocketArray()
        error = 0
        
        out = SocketArray(json.dumps(self.data))
        
        logger.log(lvl="DEBUG", msg="Outgoing Message: %s"%(out,))
            
#        except:
#            error = NO_DICT_ERROR
#            return out,error
            
        if not "event" in self.data['data'].keys():
            error = FORMAT_ERROR

        if not "content" in self.data['data'].keys():
            error = FORMAT_ERROR
        
        outstr = out.ext(EOM)
        
        logger.log(lvl="DEBUG", msg="Outgoing Message extended: %s"%(outstr,))
            
        return unicoding(outstr), error