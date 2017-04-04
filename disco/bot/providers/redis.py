from __future__ import absolute_import

import redis

from itertools import izip

from disco.util.serializer import Serializer
from .base import BaseProvider, SEP_SENTINEL


class RedisProvider(BaseProvider):
    def __init__(self, config):
        super(RedisProvider, self).__init__(config)
        self.format = config.get('format', 'pickle')
        self.conn = None

    def load(self):
        self.conn = redis.Redis(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 6379),
            db=self.config.get('db', 0))

    def exists(self, key):
        return self.conn.exists(key)

    def keys(self, other):
        count = other.count(SEP_SENTINEL) + 1
        for key in self.conn.scan_iter(u'{}*'.format(other)):
            key = key.decode('utf-8')
            if key.count(SEP_SENTINEL) == count:
                yield key

    def get_many(self, keys):
        keys = list(keys)
        if not len(keys):
            raise StopIteration

        for key, value in izip(keys, self.conn.mget(keys)):
            yield (key, Serializer.loads(self.format, value))

    def get(self, key):
        return Serializer.loads(self.format, self.conn.get(key))

    def set(self, key, value):
        self.conn.set(key, Serializer.dumps(self.format, value))

    def delete(self, key):
        self.conn.delete(key)
