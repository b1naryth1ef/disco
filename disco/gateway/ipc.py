import random
import gevent
import string
import weakref

from holster.enum import Enum

from disco.util.logging import LoggingClass
from disco.util.serializer import dump_function, load_function


def get_random_str(size):
    return ''.join([random.choice(string.printable) for _ in range(size)])


IPCMessageType = Enum(
    'CALL_FUNC',
    'GET_ATTR',
    'EXECUTE',
    'RESPONSE',
)


class GIPCProxy(LoggingClass):
    def __init__(self, obj, pipe):
        super(GIPCProxy, self).__init__()
        self.obj = obj
        self.pipe = pipe
        self.results = weakref.WeakValueDictionary()
        gevent.spawn(self.read_loop)

    def resolve(self, parts):
        base = self.obj
        for part in parts:
            base = getattr(base, part)

        return base

    def send(self, typ, data):
        self.pipe.put((typ.value, data))

    def handle(self, mtype, data):
        if mtype == IPCMessageType.CALL_FUNC:
            nonce, func, args, kwargs = data
            res = self.resolve(func)(*args, **kwargs)
            self.send(IPCMessageType.RESPONSE, (nonce, res))
        elif mtype == IPCMessageType.GET_ATTR:
            nonce, path = data
            self.send(IPCMessageType.RESPONSE, (nonce, self.resolve(path)))
        elif mtype == IPCMessageType.EXECUTE:
            nonce, raw = data
            func = load_function(raw)
            try:
                result = func(self.obj)
            except Exception:
                self.log.exception('Failed to EXECUTE: ')
                result = None

            self.send(IPCMessageType.RESPONSE, (nonce, result))
        elif mtype == IPCMessageType.RESPONSE:
            nonce, res = data
            if nonce in self.results:
                self.results[nonce].set(res)

    def read_loop(self):
        while True:
            mtype, data = self.pipe.get()

            try:
                self.handle(mtype, data)
            except:
                self.log.exception('Error in GIPCProxy:')

    def execute(self, func):
        nonce = get_random_str(32)
        raw = dump_function(func)
        self.results[nonce] = result = gevent.event.AsyncResult()
        self.pipe.put((IPCMessageType.EXECUTE.value, (nonce, raw)))
        return result

    def get(self, path):
        nonce = get_random_str(32)
        self.results[nonce] = result = gevent.event.AsyncResult()
        self.pipe.put((IPCMessageType.GET_ATTR.value, (nonce, path)))
        return result

    def call(self, path, *args, **kwargs):
        nonce = get_random_str(32)
        self.results[nonce] = result = gevent.event.AsyncResult()
        self.pipe.put((IPCMessageType.CALL_FUNC.value, (nonce, path, args, kwargs)))
        return result
