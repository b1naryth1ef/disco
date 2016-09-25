from __future__ import absolute_import

import websocket
import gevent
import six

from disco.util.logging import LoggingClass


class Websocket(LoggingClass, websocket.WebSocketApp):
    def __init__(self, *args, **kwargs):
        LoggingClass.__init__(self)
        websocket.WebSocketApp.__init__(self, *args, **kwargs)
    def _get_close_args(self, data):
        if data and len(data) >= 2:
            code = 256 * six.byte2int(data[0:1]) + six.byte2int(data[1:2])
            reason = data[2:].decode('utf-8')
            return [code, reason]
        return [None, None]

    def _callback(self, callback, *args):
        if not callback:
            return

        try:
            gevent.spawn(callback, self, *args)
        except Exception as e:
            self.log.exception('Error in Websocket callback for {}: '.format(callback))
