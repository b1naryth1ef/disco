import skema
import functools

from disco.util import skema_find_recursive_by_type


class BaseType(skema.Model):
    def on_create(self):
        pass

    def update(self, other):
        for name, field in other.__class__._fields.items():
            value = getattr(other, name)
            if value:
                setattr(self, name, value)

    @classmethod
    def create(cls, client, data):
        obj = cls(data)

        # Valdiate
        obj.validate()

        for item in skema_find_recursive_by_type(obj, skema.ModelType):
            item.client = client

        obj.client = client
        obj.on_create()
        return obj

    @classmethod
    def create_map(cls, client, data):
        return map(functools.partial(cls.create, client), data)
