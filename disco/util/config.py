import os
import six

from .serializer import Serializer


class Config(object):
    def __init__(self, obj=None):
        self.__dict__.update({
            k: getattr(self, k) for k in dir(self.__class__)
        })

        if obj:
            self.__dict__.update(obj)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    @classmethod
    def from_file(cls, path):
        inst = cls()

        with open(path, 'r') as f:
            data = f.read()

        _, ext = os.path.splitext(path)
        Serializer.check_format(ext[1:])
        inst.__dict__.update(Serializer.loads(ext[1:], data))
        return inst

    def from_prefix(self, prefix):
        prefix += '_'
        obj = {}

        for k, v in six.iteritems(self.__dict__):
            if k.startswith(prefix):
                obj[k[len(prefix):]] = v

        return Config(obj)

    def update(self, other):
        if isinstance(other, Config):
            other = other.__dict__

        self.__dict__.update(other)

    def to_dict(self):
        return self.__dict__
