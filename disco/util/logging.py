from __future__ import absolute_import

import logging


LEVEL_OVERRIDES = {
    'requests': logging.WARNING
}


def setup_logging(**kwargs):
    logging.basicConfig(**kwargs)
    for logger, level in LEVEL_OVERRIDES.items():
        logging.getLogger(logger).setLevel(level)


class LoggingClass(object):
    __slots__ = ['_log']

    @property
    def log(self):
        try:
            return self._log
        except AttributeError:
            self._log = logging.getLogger(self.__class__.__name__)
            return self._log
