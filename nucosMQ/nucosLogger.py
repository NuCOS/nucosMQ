import logging

class Logger():
    def __init__(self, name, items):
        self.logger = logging.getLogger(name)
        self.name = name
        self.items = items

    def format(self, FORMAT):
        if self.logger.handlers:
            return
        handler = logging.StreamHandler()
        formatter = logging.Formatter(FORMAT)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def level(self, loglevel):
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
        self.logger.setLevel(numeric_level)
    

    def log(self, *msgs, **logdict):
        """
        more robust version, since missing arguments in the logdict are handled correctly
        TODO: add the loglevel logic
        """
        if not msgs:
            msg = logdict.pop('msg')
        else:
            msg = msgs[0]
        for i in self.items:
            if not i in logdict.keys():
                logdict.update({i:""})
        if 'lvl' in logdict.keys():
            lvl = logdict['lvl']
            numeric_level = getattr(logging, lvl.upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % lvl)
        else:
            numeric_level = logging.INFO       
        self.logger.log(numeric_level, msg, extra=logdict)
