import six


def to_snowflake(i):
    if isinstance(i, six.integer_types):
        return i
    elif isinstance(i, str):
        return int(i)
    elif hasattr(i, 'id'):
        return i.id

    raise Exception('{} ({}) is not convertable to a snowflake'.format(type(i), i))
