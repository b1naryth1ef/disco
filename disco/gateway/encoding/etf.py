import six

from websocket import ABNF
from erlpack import Atom, unpack, pack

from disco.gateway.encoding.base import BaseEncoder


def make_keys_atom(obj):
    res = {}
    for k, v in six.iteritems(obj):
        if isinstance(v, dict):
            v = make_keys_atom(v)
        res[Atom(k)] = v
    return res


class ETFEncoder(BaseEncoder):
    TYPE = 'etf'
    OPCODE = ABNF.OPCODE_BINARY

    @staticmethod
    def encode(obj):
        return pack(obj)

    @staticmethod
    def decode(obj):
        return unpack(obj)
