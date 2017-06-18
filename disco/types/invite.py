from disco.types.base import SlottedModel, Field, datetime
from disco.types.user import User
from disco.types.guild import Guild
from disco.types.channel import Channel


class Invite(SlottedModel):
    """
    An invite object.

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
        The time after this invite's creation at which it expires.
    max_uses : int
        The maximum number of uses.
    uses : int
        The current number of times the invite was used.
    temporary : bool
        Whether this invite only grants temporary membership.
    created_at : datetime
        When this invite was created.
    """
    code = Field(str)
    inviter = Field(User)
    guild = Field(Guild)
    channel = Field(Channel)
    max_age = Field(int)
    max_uses = Field(int)
    uses = Field(int)
    temporary = Field(bool)
    created_at = Field(datetime)

    @classmethod
    def create_for_channel(cls, channel, *args, **kwargs):
        return channel.client.api.channels_invites_create(channel.id, *args, **kwargs)

    def delete(self, *args, **kwargs):
        self.client.api.invites_delete(self.code, *args, **kwargs)
