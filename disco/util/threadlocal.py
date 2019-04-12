import gevent
import weakref


class ThreadLocal(object):
    ___slots__ = ['storage']

    def __init__(self):
        self.storage = weakref.WeakKeyDictionary()

    def get(self):
        if gevent.getcurrent() not in self.storage:
            self.storage[gevent.getcurrent()] = {}
        return self.storage[gevent.getcurrent()]

    def drop(self):
        if gevent.getcurrent() in self.storage:
            del self.storage[gevent.getcurrent()]

    def __contains__(self, key):
        return key in self.get()

    def __getitem__(self, item):
        return self.get()[item]

    def __setitem__(self, item, value):
        self.get()[item] = value
