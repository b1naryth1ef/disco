import six


def get_enum_members(enum):
    for k, v in six.iteritems(enum.__dict__):
        if not isinstance(k, six.string_types):
            continue

        if k.startswith('_') or not k.isupper():
            continue

        yield k, v


def get_enum_value_by_name(enum, name):
    name = name.lower()

    for k, v in get_enum_members(enum):
        if k.lower() == name:
            return v
