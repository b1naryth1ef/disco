from __future__ import absolute_import, print_function

try:
    import ujson as json
except ImportError:
    import json

from disco.gateway.encoding.base import BaseEncoder


class JSONEncoder(BaseEncoder):
    TYPE = 'json'

    @staticmethod
    def encode(obj):
        return json.dumps(obj)

    @staticmethod
    def decode(obj):
        return json.loads(obj)
