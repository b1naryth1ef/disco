import six
from websocket import ABNF

from disco.gateway.encoding.base import BaseEncoder

if six.PY3:
    from earl import unpack, pack
else:
    from erlpack import unpack, pack


class ETFEncoder(BaseEncoder):
    TYPE = 'etf'
    OPCODE = ABNF.OPCODE_BINARY

    @staticmethod
    def encode(obj):
        return pack(obj)

    @staticmethod
    def decode(obj):
        if six.PY3:
            return unpack(obj, encoding='utf-8', encode_binary_ext=True)
        return unpack(obj)
