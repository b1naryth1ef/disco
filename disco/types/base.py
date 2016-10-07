import six
import inspect
import functools

from datetime import datetime as real_datetime

DATETIME_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S'
]


def _make(typ, data, client):
    if inspect.isfunction(typ):
        args, _, _, _ = inspect.getargspec(typ)
        if 'client' in args:
            return typ(data, client)
    elif issubclass(typ, Model):
        if not client:
            raise Exception()
        return typ(data, client)
    return typ(data)


def snowflake(data):
    return int(data) if data else None


def enum(typ):
    def _f(data):
        return typ.get(data) if data else None
    return _f


def listof(typ):
    def _f(data, client=None):
        if not data:
            return []
        return [_make(typ, obj, client) for obj in data]
    return _f


def dictof(typ, key=None):
    def _f(data, client=None):
        if not data:
            return {}

        if key:
            return {
                getattr(v, key): v for v in (
                    _make(typ, i, client) for i in data
                )}
        else:
            return {k: _make(typ, v, client) for k, v in six.iteritems(data)}
    return _f


def alias(typ, name):
    return ('alias', name, typ)


def datetime(data):
    if not data:
        return None

    for fmt in DATETIME_FORMATS:
        try:
            return real_datetime.strptime(data.rsplit('+', 1)[0], fmt)
        except (ValueError, TypeError):
            continue

    raise ValueError('Failed to conver `{}` to datetime'.format(data))


def text(obj):
    return six.text_type(obj) if obj else six.text_type()


def binary(obj):
    return six.text_type(obj) if obj else six.text_type()


class ModelMeta(type):
    def __new__(cls, name, parents, dct):
        fields = {}
        for k, v in six.iteritems(dct):
            if isinstance(v, tuple):
                if v[0] == 'alias':
                    fields[v[1]] = (k, v[2])
                    continue

            if inspect.isclass(v):
                fields[k] = v
            elif callable(v):
                args, _, _, _ = inspect.getargspec(v)
                if 'self' in args:
                    continue

                fields[k] = v

        dct['_fields'] = fields
        return super(ModelMeta, cls).__new__(cls, name, parents, dct)


class Model(six.with_metaclass(ModelMeta)):
    def __init__(self, obj, client=None):
        self.client = client

        for name, typ in self.__class__._fields.items():
            dest_name = name

            if isinstance(typ, tuple):
                dest_name, typ = typ

            if name not in obj or not obj[name]:
                if inspect.isclass(typ) and issubclass(typ, Model):
                    res = None
                elif isinstance(typ, type):
                    res = typ()
                else:
                    res = typ(None)
                setattr(self, dest_name, res)
                continue

            try:
                if client and inspect.isfunction(typ):
                    args, _, _, _ = inspect.getargspec(typ)
                    if 'client' in args:
                        v = typ(obj[name], client)
                    else:
                        v = typ(obj[name])
                elif inspect.isclass(typ) and issubclass(typ, Model):
                    v = typ(obj[name], client)
                else:
                    v = typ(obj[name])
            except Exception:
                print('Failed during parsing of field {} => {}'.format(name, typ))
                raise

            setattr(self, dest_name, v)

    def update(self, other):
        for name in six.iterkeys(self.__class__._fields):
            value = getattr(other, name)
            if value:
                setattr(self, name, value)

        # Clear cached properties
        for name in dir(type(self)):
            if isinstance(getattr(type(self), name), property):
                try:
                    delattr(self, name)
                except:
                    pass

    @classmethod
    def create(cls, client, data):
        return cls(data, client)

    @classmethod
    def create_map(cls, client, data):
        return list(map(functools.partial(cls.create, client), data))
