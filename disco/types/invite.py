import skema

from disco.util.types import PreHookType
from disco.types.base import BaseType
from disco.types.user import User
from disco.types.guild import Guild
from disco.types.channel import Channel


class Invite(BaseType):
    """
    An invite object

    Attributes
    ----------
    code : str
        The invite code.
    inviter : :class:`disco.types.user.User`
        The user who created this invite.
    guild : :class:`disco.types.guild.Guild`
        The guild this invite is for.
    channel : :class:`disco.types.channel.Channel`
        The channel this invite is for.
    max_age : int
        The time after this invites creation at which it expires.
    max_uses : int
        The maximum number of uses.
    uses : int
        The current number of times the invite was used.
    temporary : bool
        Whether this invite only grants temporary memborship.
    created_at : datetime
        When this invite was created.
    """
    code = skema.StringType()

    inviter = skema.ModelType(User)
    guild = skema.ModelType(Guild)
    channel = skema.ModelType(Channel)

    max_age = skema.IntType()
    max_uses = skema.IntType()
    uses = skema.IntType()
    temporary = skema.BooleanType()

    created_at = PreHookType(lambda k: k[:-6], skema.DateTimeType())
