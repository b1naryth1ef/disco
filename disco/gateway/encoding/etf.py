from websocket import ABNF
from erlpack import unpack, pack

from disco.gateway.encoding.base import BaseEncoder


class ETFEncoder(BaseEncoder):
    TYPE = 'etf'
    OPCODE = ABNF.OPCODE_BINARY

    @staticmethod
    def encode(obj):
        return pack(obj)

    @staticmethod
    def decode(obj):
        return unpack(obj)
