import skema

from disco.util import recursive_find_matching


class BaseType(skema.Model):
    @classmethod
    def create(cls, client, data):
        obj = cls(data)

        # Valdiate
        obj.validate()

        # TODO: this can be smarter using skema metadata
        for item in recursive_find_matching(obj, lambda v: isinstance(v, BaseType)):
            item.client = client

        obj.client = client
        return obj
