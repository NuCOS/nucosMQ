import json

EOM = "_EOM_" #put a fancy message-limiter inside

NO_DICT_ERROR = 2
FORMAT_ERROR = 1

class NucosIncomingMessage():
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
    #TODO check if data is a well formed input
    def __init__(self, data):
        self.data = { "data": data }
    def payload(self):
        return ''.join([json.dumps(self.data), EOM])