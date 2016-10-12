import six

from six.moves import filter, map, UserDict
from collections import defaultdict


class HashMap(UserDict):
    def iter(self):
        return iter(self.data)

    def items(self):
        return six.iteritems(self.data)

    def keys(self):
        return six.iterkeys(self.data)

    def values(self):
        return six.itervalues(self.data)

    def find(self, predicate):
        if not callable(predicate):
            raise TypeError('predicate must be callable')

        for obj in self.values():
            if predicate(obj):
                yield obj

    def find_one(self, predicate):
        return next(self.find(predicate), None)

    def select(self, *args, **kwargs):
        if kwargs:
            args += tuple([kwargs])

        for obj in self.values():
            for check in args:
                for k, v in six.iteritems(check):
                    if getattr(obj, k) != v:
                        break
                    yield obj

    def select_one(self, **kwargs):
        return next(self.select(**kwargs), None)

    def filter(self, predicate):
        if not callable(predicate):
            raise TypeError('predicate must be callable')
        return filter(self.values(), predicate)

    def map(self, predicate):
        if not callable(predicate):
            raise TypeError('predicate must be callable')
        return map(self.values(), predicate)


class DefaultHashMap(defaultdict, HashMap):
    pass
