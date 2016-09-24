import skema

from disco.util.types import PreHookType
from disco.types.base import BaseType
from disco.types.user import User
from disco.types.guild import Guild
from disco.types.channel import Channel


class Invite(BaseType):
    code = skema.StringType()

    inviter = skema.ModelType(User)
    guild = skema.ModelType(Guild)
    channel = skema.ModelType(Channel)

    max_age = skema.IntType()
    max_uses = skema.IntType()
    uses = skema.IntType()
    temporary = skema.BooleanType()

    created_at = PreHookType(lambda k: k[:-6], skema.DateTimeType())
