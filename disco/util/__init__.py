import skema


def to_snowflake(i):
    if isinstance(i, long):
        return i
    elif isinstance(i, str):
        return long(i)
    elif hasattr(i, 'id'):
        return i.id

    raise Exception('{} ({}) is not convertable to a snowflake'.format(type(i), i))


def _recurse(typ, field, value):
    result = []

    if isinstance(field, skema.ModelType):
        result += skema_find_recursive_by_type(value, typ)

    if isinstance(field, (skema.ListType, skema.SetType, skema.DictType)):
        if isinstance(field, skema.DictType):
            value = value.values()

        for item in value:
            if isinstance(field.field, typ):
                result.append(item)
            result += _recurse(typ, field.field, item)

    return result


def skema_find_recursive_by_type(base, typ):
    result = []

    for name, field in base._fields_by_stored_name.items():
        v = getattr(base, name, None)

        if not v:
            continue

        if isinstance(field, typ):
            result.append(v)

        result += _recurse(typ, field, v)

    return result
