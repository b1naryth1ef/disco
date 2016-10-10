from __future__ import absolute_import

import six
import rocksdb

from itertools import izip
from six.moves import map

from disco.util.serializer import Serializer
from .base import BaseProvider, SEP_SENTINEL


class RocksDBProvider(BaseProvider):
    def __init__(self, config):
        self.config = config
        self.format = config.get('format', 'pickle')
        self.path = config.get('path', 'storage.db')

    def k(self, k):
        return bytes(k) if six.PY3 else str(k.encode('utf-8'))

    def load(self):
        self.db = rocksdb.DB(self.path, rocksdb.Options(create_if_missing=True))

    def exists(self, key):
        return self.db.get(self.k(key)) is not None

    # TODO prefix extractor
    def keys(self, other):
        count = other.count(SEP_SENTINEL) + 1
        it = self.db.iterkeys()
        it.seek_to_first()

        for key in it:
            key = key.decode('utf-8')
            if key.startswith(other) and key.count(SEP_SENTINEL) == count:
                yield key

    def get_many(self, keys):
        for key, value in izip(keys, self.db.multi_get(list(map(self.k, keys)))):
            yield (key, Serializer.loads(self.format, value.decode('utf-8')))

    def get(self, key):
        return Serializer.loads(self.format, self.db.get(self.k(key)).decode('utf-8'))

    def set(self, key, value):
        self.db.put(self.k(key), Serializer.dumps(self.format, value))

    def delete(self, key):
        self.db.delete(self.k(key))
