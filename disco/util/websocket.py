from __future__ import absolute_import

import sys
import ssl
import websocket
import gevent
import six
import gipc
import signal

from holster.emitter import Emitter

from disco.util.logging import LoggingClass


class Websocket(LoggingClass, websocket.WebSocketApp):
    """
    Subclass of websocket.WebSocketApp that adds some important improvements:
        - Passes exit code to on_error callback in all cases
        - Spawns callbacks in a gevent greenlet, and catches/logs exceptions
    """
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
        except Exception:
            self.log.exception('Error in Websocket callback for {}: '.format(callback))


class WebsocketProcess(Websocket):
    def __init__(self, pipe, *args, **kwargs):
        Websocket.__init__(self, *args, **kwargs)
        self.pipe = pipe

        # Hack to get events to emit
        for var in self.__dict__.keys():
            if not var.startswith('on_'):
                continue

            setattr(self, var, var)

    def _callback(self, callback, *args):
        if not callback:
            return

        self.pipe.put((callback, args))


class WebsocketProcessProxy(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.emitter = Emitter(gevent.spawn)

        gevent.signal(signal.SIGINT, self.handle_signal)
        gevent.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, *args):
        self.close()
        gevent.sleep(1)
        self.process.terminate()
        sys.exit()

    @classmethod
    def process(cls, pipe, *args, **kwargs):
        proc = WebsocketProcess(pipe, *args, **kwargs)

        # TODO: ssl?
        gevent.spawn(proc.run_forever, sslopt={'cert_reqs': ssl.CERT_NONE})

        while True:
            op = pipe.get()
            getattr(proc, op['method'])(*op['args'], **op['kwargs'])

    def read_task(self):
        while True:
            try:
                name, args = self.pipe.get()
            except EOFError:
                return
            self.emitter.emit(name, *args)

    def run_forever(self):
        self.pipe, pipe = gipc.pipe(True)
        self.process = gipc.start_process(self.process, args=tuple([pipe] + list(self.args)), kwargs=self.kwargs)
        self.read_task()

    def __getattr__(self, attr):
        def _wrapped(*args, **kwargs):
            self.pipe.put({'method': attr, 'args': args, 'kwargs': kwargs})

        return _wrapped
