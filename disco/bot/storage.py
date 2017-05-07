import os

from six.moves import UserDict

from disco.util.hashmap import HashMap
from disco.util.serializer import Serializer


class StorageHashMap(HashMap):
    def __init__(self, data):
        self.data = data


class ContextAwareProxy(UserDict):
    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def data(self):
        return self.ctx()


class StorageDict(UserDict):
    def __init__(self, parent, data):
        self._parent = parent
        self.data = data

    def update(self, other):
        self.data.update(other)
        self._parent._update()

    def __setitem__(self, key, value):
        self.data[key] = value
        self._parent._update()

    def __delitem__(self, key):
        del self.data[key]
        self._parent._update()


class Storage(object):
    def __init__(self, ctx, config):
        self._ctx = ctx
        self._path = config.path
        self._serializer = config.serializer
        self._fsync = config.fsync
        self._data = {}

        if os.path.exists(self._path):
            with open(self._path, 'r') as f:
                self._data = Serializer.loads(self._serializer, f.read())
                if not self._data:
                    self._data = {}

    def __getitem__(self, key):
        if key not in self._data:
            self._data[key] = {}
        return StorageHashMap(StorageDict(self, self._data[key]))

    def _update(self):
        if self._fsync:
            self.save()

    def save(self):
        if not self._path:
            return

        with open(self._path, 'w') as f:
            f.write(Serializer.dumps(self._serializer, self._data))

    def guild(self, key):
        return ContextAwareProxy(
            lambda: self['_g{}:{}'.format(self._ctx['guild'].id, key)]
        )

    def channel(self, key):
        return ContextAwareProxy(
            lambda: self['_c{}:{}'.format(self._ctx['channel'].id, key)]
        )

    def plugin(self, key):
        return ContextAwareProxy(
            lambda: self['_p{}:{}'.format(self._ctx['plugin'].name, key)]
        )

    def user(self, key):
        return ContextAwareProxy(
            lambda: self['_u{}:{}'.format(self._ctx['user'].id, key)]
        )
