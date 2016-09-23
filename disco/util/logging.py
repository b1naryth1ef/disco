from __future__ import absolute_import

import logging


class LoggingClass(object):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def log_on_error(self, msg, f):
        def _f(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                self.log.exception(msg)
                raise
        return _f
