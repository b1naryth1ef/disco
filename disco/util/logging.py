from __future__ import absolute_import

import logging


class LoggingClass(object):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
