from skema import BaseType


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
