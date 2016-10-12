import six

from six.moves import filter, map
from collections import defaultdict
from UserDict import IterableUserDict


class HashMap(IterableUserDict):
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

    def select(self, **kwargs):
        for obj in self.values():
            for k, v in six.iteritems(kwargs):
                if getattr(obj, k) != v:
                    continue
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
