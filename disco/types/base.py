import skema
import functools

from disco.util import skema_find_recursive_by_type


class BaseType(skema.Model):
    @classmethod
    def create(cls, client, data):
        obj = cls(data)

        # Valdiate
        obj.validate()

        for item in skema_find_recursive_by_type(obj, skema.ModelType):
            item.client = client

        obj.client = client
        return obj

    @classmethod
    def create_map(cls, client, data):
        return map(functools.partial(cls.create, client), data)
