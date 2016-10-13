from __future__ import absolute_import

import redis

from itertools import izip

from disco.util.serializer import Serializer
from .base import BaseProvider, SEP_SENTINEL


class RedisProvider(BaseProvider):
    def __init__(self, config):
        self.config = config

    def load(self):
        self.redis = redis.Redis(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 6379),
            db=self.config.get('db', 0))

    def exists(self, key):
        return self.db.exists(key)

    def keys(self, other):
        count = other.count(SEP_SENTINEL) + 1
        for key in self.db.scan_iter(u'{}*'.format(other)):
            if key.count(SEP_SENTINEL) == count:
                yield key

    def get_many(self, keys):
        for key, value in izip(keys, self.db.mget(keys)):
            yield (key, Serializer.loads(self.format, value))

    def get(self, key):
        return Serializer.loads(self.format, self.db.get(key))

    def set(self, key, value):
        self.db.set(key, Serializer.dumps(self.format, value))

    def delete(self, key, value):
        self.db.delete(key)
