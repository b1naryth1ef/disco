import random
import gipc
import gevent
import string
import weakref


def get_random_str(size):
    return ''.join([random.choice(string.ascii_printable) for _ in range(size)])


class GIPCProxy(object):
    def __init__(self, pipe):
        self.pipe = pipe
        self.results = weakref.WeakValueDictionary()
        gevent.spawn(self.read_loop)

    def read_loop(self):
        while True:
            nonce, data = self.pipe.get()
            if nonce in self.results:
                self.results[nonce].set(data)

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            nonce = get_random_str()
            self.results[nonce] = gevent.event.AsyncResult()
            self.pipe.put(nonce, name, args, kwargs)
            return self.results[nonce]
        return wrapper


class GIPCObject(object):
    def __init__(self, inst, pipe):
        self.inst = inst
        self.pipe = pipe
        gevent.spawn(self.read_loop)

    def read_loop(self):
        while True:
            nonce, func, args, kwargs = self.pipe.get()
            func = getattr(self.inst, func)
            self.pipe.put((nonce, func(*args, **kwargs)))

class IPC(object):
    def __init__(self, sharder):
        self.sharder = sharder

    def get_shards(self):
        return {}
