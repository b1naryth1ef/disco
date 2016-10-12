import six
import pickle

from six.moves import map, UserDict


ROOT_SENTINEL = u'\u200B'
SEP_SENTINEL = u'\u200D'
OBJ_SENTINEL = u'\u200C'
CAST_SENTINEL = u'\u24EA'


def join_key(*args):
    nargs = []
    for arg in args:
        if not isinstance(arg, six.string_types):
            arg = CAST_SENTINEL + pickle.dumps(arg)
        nargs.append(arg)
    return SEP_SENTINEL.join(nargs)


def true_key(key):
    key = key.rsplit(SEP_SENTINEL, 1)[-1]
    if key.startswith(CAST_SENTINEL):
        return pickle.loads(key)
    return key


class BaseProvider(object):
    def __init__(self, config):
        self.config = config
        self.data = {}

    def exists(self, key):
        return key in self.data

    def keys(self, other):
        count = other.count(SEP_SENTINEL) + 1
        for key in self.data.keys():
            if key.startswith(other) and key.count(SEP_SENTINEL) == count:
                yield key

    def get_many(self, keys):
        for key in keys:
            yield key, self.get(key)

    def get(self, key):
        return self.data[key]

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        del self.data[key]

    def load(self):
        pass

    def save(self):
        pass

    def root(self):
        return StorageDict(self)


class StorageDict(UserDict):
    def __init__(self, parent_or_provider, key=None):
        if isinstance(parent_or_provider, BaseProvider):
            self.provider = parent_or_provider
            self.parent = None
        else:
            self.parent = parent_or_provider
            self.provider = self.parent.provider
        self._key = key or ROOT_SENTINEL

    def keys(self):
        return map(true_key, self.provider.keys(self.key))

    def values(self):
        for key in self.keys():
            yield self.provider.get(key)

    def items(self):
        for key in self.keys():
            yield (true_key(key), self.provider.get(key))

    def ensure(self, key, typ=dict):
        if key not in self:
            self[key] = typ()
        return self[key]

    def update(self, obj):
        for k, v in six.iteritems(obj):
            self[k] = v

    @property
    def data(self):
        obj = {}

        for raw, value in self.provider.get_many(self.provider.keys(self.key)):
            key = true_key(raw)

            if value == OBJ_SENTINEL:
                value = self.__class__(self, key=key).data
            obj[key] = value
        return obj

    @property
    def key(self):
        if self.parent is not None:
            return join_key(self.parent.key, self._key)
        return self._key

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            obj = self.__class__(self, key)
            obj.update(value)
            value = OBJ_SENTINEL

        self.provider.set(join_key(self.key, key), value)

    def __getitem__(self, key):
        res = self.provider.get(join_key(self.key, key))

        if res == OBJ_SENTINEL:
            return self.__class__(self, key)

        return res

    def __delitem__(self, key):
        return self.provider.delete(join_key(self.key, key))

    def __contains__(self, key):
        return self.provider.exists(join_key(self.key, key))
