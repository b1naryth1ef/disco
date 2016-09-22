import skema

from disco.types.base import BaseType


class VoiceState(BaseType):
    id = skema.SnowflakeType()
