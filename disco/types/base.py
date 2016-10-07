import six
import inspect
import functools

from datetime import datetime as real_datetime


def snowflake(data):
    return int(data)


def enum(typ):
    def _f(data):
        return typ.get(data)
    return _f


def listof(typ):
    def _f(data):
        return list(map(typ, data))
    return _f


def dictof(typ, key=None):
    def _f(data):
        if key:
            return {getattr(v, key): v for v in map(typ, data)}
        else:
            return {k: typ(v) for k, v in six.iteritems(data)}
    return _f


def alias(typ, name):
    return ('alias', name, typ)


def datetime(typ):
    return real_datetime.strptime(typ.rsplit('+', 1)[0], '%Y-%m-%dT%H:%M:%S.%f')


def text(obj):
    return six.text_type(obj)


def binary(obj):
    return six.text_type(obj)


class ModelMeta(type):
    def __new__(cls, name, parents, dct):
        fields = {}
        for k, v in six.iteritems(dct):
            if isinstance(v, tuple):
                if v[0] == 'alias':
                    fields[v[1]] = (k, v[2])
                    continue

            if callable(v) or inspect.isclass(v):
                fields[k] = v

        dct['_fields'] = fields
        return super(ModelMeta, cls).__new__(cls, name, parents, dct)


class Model(six.with_metaclass(ModelMeta)):
    def __init__(self, obj, client=None):
        for name, typ in self.__class__._fields.items():
            dest_name = name

            if isinstance(typ, tuple):
                dest_name, typ = typ

            if name not in obj or not obj[name]:
                continue

            try:
                v = typ(obj[name])
            except TypeError as e:
                print('Failed during parsing of field {} => {} (`{}`)'.format(name, typ, obj[name]))
                raise e

            if client and isinstance(v, Model):
                v.client = client

            setattr(self, dest_name, v)

    def update(self, other):
        for name in six.iterkeys(self.__class__.fields):
            value = getattr(other, name)
            if value:
                setattr(self, name, value)

    @classmethod
    def create(cls, client, data):
        return cls(data)

    @classmethod
    def create_map(cls, client, data):
        return map(functools.partial(cls.create, client), data)
