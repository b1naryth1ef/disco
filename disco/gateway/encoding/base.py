from websocket import ABNF

from holster.interface import Interface


class BaseEncoder(Interface):
    TYPE = None
    OPCODE = ABNF.OPCODE_TEXT

    @staticmethod
    def encode(obj):
        pass

    @staticmethod
    def decode(obj):
        pass
