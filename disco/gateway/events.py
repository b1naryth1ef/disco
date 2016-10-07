import inflection
import six

from disco.types import Guild, Channel, User, GuildMember, Role, Message, VoiceState
from disco.types.base import Model, Field, snowflake, listof, text


# TODO: clean this... use BaseType, etc
class GatewayEvent(Model):
    @staticmethod
    def from_dispatch(client, data):
        cls = globals().get(inflection.camelize(data['t'].lower()))
        if not cls:
            raise Exception('Could not find cls for {}'.format(data['t']))

        return cls.create(data['d'], client)

    @classmethod
    def create(cls, obj, client):
        # If this event is wrapping a model, pull its fields
        if hasattr(cls, '_wraps_model'):
            alias, model = cls._wraps_model

            data = {
                k: obj.pop(k) for k in six.iterkeys(model._fields) if k in obj
            }

            obj[alias] = data

        return cls(obj, client)

    def __getattr__(self, name):
        if hasattr(self, '_wraps_model'):
            modname, _ = self._wraps_model
            if hasattr(self, modname) and hasattr(getattr(self, modname), name):
                return getattr(getattr(self, modname), name)
        return object.__getattr__(self, name)


def wraps_model(model, alias=None):
    alias = alias or model.__name__.lower()

    def deco(cls):
        cls._fields[alias] = Field(model)
        cls._fields[alias].set_name(alias)
        cls._wraps_model = (alias, model)
        return cls
    return deco


class Ready(GatewayEvent):
    """
    Sent after the initial gateway handshake is complete. Contains data required
    for bootstrapping the clients states.
    """
    version = Field(int, alias='v')
    session_id = Field(str)
    user = Field(User)
    guilds = Field(listof(Guild))


class Resumed(GatewayEvent):
    """
    Sent after a resume completes.
    """
    pass


@wraps_model(Guild)
class GuildCreate(GatewayEvent):
    """
    Sent when a guild is created, or becomes available.
    """
    unavailable = Field(bool)


@wraps_model(Guild)
class GuildUpdate(GatewayEvent):
    """
    Sent when a guild is updated.
    """
    pass


class GuildDelete(GatewayEvent):
    """
    Sent when a guild is deleted, or becomes unavailable.
    """
    id = Field(snowflake)
    unavailable = Field(bool)


@wraps_model(Channel)
class ChannelCreate(GatewayEvent):
    """
    Sent when a channel is created.
    """


@wraps_model(Channel)
class ChannelUpdate(ChannelCreate):
    """
    Sent when a channel is updated.
    """
    pass


@wraps_model(Channel)
class ChannelDelete(ChannelCreate):
    """
    Sent when a channel is deleted.
    """
    pass


class ChannelPinsUpdate(GatewayEvent):
    """
    Sent when a channels pins are updated.
    """
    channel_id = Field(snowflake)
    last_pin_timestamp = Field(int)


@wraps_model(User)
class GuildBanAdd(GatewayEvent):
    """
    Sent when a user is banned from a guild.
    """
    pass


@wraps_model(User)
class GuildBanRemove(GuildBanAdd):
    """
    Sent when a user is unbanned from a guild.
    """
    pass


class GuildEmojisUpdate(GatewayEvent):
    """
    Sent when a guilds emojis are updated.
    """
    pass


class GuildIntegrationsUpdate(GatewayEvent):
    """
    Sent when a guilds integrations are updated.
    """
    pass


class GuildMembersChunk(GatewayEvent):
    """
    Sent in response to a members chunk request.
    """
    guild_id = Field(snowflake)
    members = Field(listof(GuildMember))


@wraps_model(GuildMember, alias='member')
class GuildMemberAdd(GatewayEvent):
    """
    Sent when a user joins a guild.
    """
    pass


class GuildMemberRemove(GatewayEvent):
    """
    Sent when a user leaves a guild (via leaving, kicking, or banning).
    """
    guild_id = Field(snowflake)
    user = Field(User)


@wraps_model(GuildMember, alias='member')
class GuildMemberUpdate(GatewayEvent):
    """
    Sent when a guilds member is updated.
    """
    pass


class GuildRoleCreate(GatewayEvent):
    """
    Sent when a role is created.
    """
    guild_id = Field(snowflake)
    role = Field(Role)


class GuildRoleUpdate(GuildRoleCreate):
    """
    Sent when a role is updated.
    """
    pass


class GuildRoleDelete(GuildRoleCreate):
    """
    Sent when a role is deleted.
    """
    pass


@wraps_model(Message)
class MessageCreate(GatewayEvent):
    """
    Sent when a message is created.
    """


@wraps_model(Message)
class MessageUpdate(MessageCreate):
    """
    Sent when a message is updated/edited.
    """
    pass


class MessageDelete(GatewayEvent):
    """
    Sent when a message is deleted.
    """
    id = Field(snowflake)
    channel_id = Field(snowflake)


class MessageDeleteBulk(GatewayEvent):
    """
    Sent when multiple messages are deleted from a channel.
    """
    channel_id = Field(snowflake)
    ids = Field(listof(snowflake))


class PresenceUpdate(GatewayEvent):
    """
    Sent when a users presence is updated.
    """
    class Game(Model):
        # TODO enum
        type = Field(int)
        name = Field(text)
        url = Field(text)

    user = Field(User)
    guild_id = Field(snowflake)
    roles = Field(listof(snowflake))
    game = Field(Game)
    status = Field(text)


class TypingStart(GatewayEvent):
    """
    Sent when a user begins typing in a channel.
    """
    channel_id = Field(snowflake)
    user_id = Field(snowflake)
    timestamp = Field(snowflake)


@wraps_model(VoiceState, alias='state')
class VoiceStateUpdate(GatewayEvent):
    """
    Sent when a users voice state changes.
    """
    pass


class VoiceServerUpdate(GatewayEvent):
    """
    Sent when a voice server is updated.
    """
    token = Field(str)
    endpoint = Field(str)
    guild_id = Field(snowflake)
