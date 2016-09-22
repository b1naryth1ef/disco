import inspect


class TypedClassException(Exception):
    pass


def construct_typed_class(cls, data):
    obj = cls()
    load_typed_class(obj, data)
    return obj


def get_field_and_alias(field):
    if isinstance(field, tuple):
        return field
    else:
        return field, field


def get_optional(typ):
    if isinstance(typ, tuple) and len(typ) == 1:
        return True, typ[0]
    return False, typ


def cast(typ, value):
    valid = True

    # TODO: better exceptions
    if isinstance(typ, list):
        if typ:
            typ = typ[0]
            value = map(typ, value)
        else:
            list(value)
    elif isinstance(typ, dict):
        if typ:
            ktyp, vtyp = typ.items()[0]
            value = {ktyp(k): vtyp(v) for k, v in typ.items()}
        else:
            dict(value)
    elif isinstance(typ, set):
        if typ:
            typ = list(typ)[0]
            value = set(map(typ, value))
        else:
            set(value)
    elif isinstance(typ, str):
        valid = False
    elif not isinstance(value, typ):
        value = typ(value)

    return valid, value


def load_typed_class(obj, params, data):
    print obj, params, data
    for field, typ in params.items():
        field, alias = get_field_and_alias(field)

        # Skipped field
        if typ is None:
            continue

        optional, typ = get_optional(typ)
        if field not in data and not optional:
            raise TypedClassException('Missing value for attribute `{}`'.format(field))

        value = data[field]

        print field, alias, value, typ
        if value is None:
            if not optional:
                raise TypedClassException('Non-optional attribute `{}` cannot take None'.format(field))
        else:
            valid, value = cast(typ, value)
            if not valid:
                continue

        setattr(obj, alias, value)


def dump_typed_class(obj, params):
    data = {}

    for field, typ in params.items():
        field, alias = get_field_and_alias(field)

        value = getattr(obj, alias, None)

        if typ is None:
            data[field] = typ
            continue

        optional, typ = get_optional(typ)
        if not value and not optional:
            raise TypedClassException('Missing value for attribute `{}`'.format(field))

        _, value = cast(typ, value)
        data[field] = value

    return data


def get_params(obj):
    assert(issubclass(obj.__class__, TypedClass))

    if not hasattr(obj.__class__, '_cached_oop_params'):
        base = {}
        for cls in reversed(inspect.getmro(obj.__class__)):
            base.update(getattr(cls, 'PARAMS', {}))
        obj.__class__._cached_oop_params = base
    return obj.__class__._cached_oop_params


def load_typed_instance(obj, data):
    return load_typed_class(obj, get_params(obj), data)


class TypedClass(object):
    def __init__(self, **kwargs):
        # TODO: validate
        self.__dict__.update(kwargs)

    @classmethod
    def from_dict(cls, data):
        self = cls()
        load_typed_instance(self, data)
        return self

    def to_dict(self):
        return dump_typed_class(self, get_params(self))


def require_implementation(attr):
    def _f(self, *args, **kwargs):
        raise NotImplementedError('{} must implement method {}', self.__class__.__name, attr)
    return _f
