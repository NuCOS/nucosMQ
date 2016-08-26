import json

EOM = "_EOM_" #put a fancy message-limiter inside

NO_DICT_ERROR = 2
FORMAT_ERROR = 1

class NucosIncomingMessage():
    """
    simple incoming message protocol
    
    message contains an event and content
    """
    def __init__(self, payload):
        self.payload = payload
    def msgs(self):
        error = 0
        msgs = self.payload.split(EOM)
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
        return out, error # a list of dicts, one or maybe several
    
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
        out = str()
        error = 0
        try:
            out = json.dumps(self.data)
        except:
            error = NO_DICT_ERROR
            return out,error
            
        if not "event" in self.data['data'].keys():
            error = FORMAT_ERROR

        if not "content" in self.data['data'].keys():
            error = FORMAT_ERROR
            
        return ''.join([out, EOM]), error