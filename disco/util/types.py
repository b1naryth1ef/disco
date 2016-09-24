from skema import BaseType, DictType


class PreHookType(BaseType):
    _hashable = False

    def __init__(self, func, field, **kwargs):
        self.func = func
        self.field = field

        super(PreHookType, self).__init__(**kwargs)

    def to_python(self, value):
        value = self.func(value)
        return self.field.to_python(value)

    def to_storage(self, *args, **kwargs):
        return self.field.to_storage(*args, **kwargs)


class ListToDictType(DictType):
    def __init__(self, key, *args, **kwargs):
        super(ListToDictType, self).__init__(*args, **kwargs)
        self.key = key

    def to_python(self, value):
        if not value:
            return {}

        to_python = self.field.to_python

        obj = {}
        for item in value:
            item = to_python(item)
            obj[getattr(item, self.key)] = item
        return obj
