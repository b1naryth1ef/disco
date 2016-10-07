import inflection
import six

from disco.types import Guild, Channel, User, GuildMember, Role, Message, VoiceState
from disco.types.base import Model, snowflake, alias, listof


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


def wraps_model(model, alias=None):
    alias = alias or model.__name__.lower()

    def deco(cls):
        cls._fields[alias] = model
        cls._wraps_model = (alias, model)
        return cls
    return deco


class Ready(GatewayEvent):
    version = alias(int, 'v')
    session_id = str
    user = User
    guilds = listof(Guild)


class Resumed(GatewayEvent):
    pass


@wraps_model(Guild)
class GuildCreate(GatewayEvent):
    unavailable = bool


@wraps_model(Guild)
class GuildUpdate(GatewayEvent):
    pass


class GuildDelete(GatewayEvent):
    id = snowflake
    unavailable = bool


@wraps_model(Channel)
class ChannelCreate(GatewayEvent):
    @property
    def guild(self):
        return self.channel.guild


@wraps_model(Channel)
class ChannelUpdate(ChannelCreate):
    pass


@wraps_model(Channel)
class ChannelDelete(ChannelCreate):
    pass


class ChannelPinsUpdate(GatewayEvent):
    channel_id = snowflake
    last_pin_timestamp = int


@wraps_model(User)
class GuildBanAdd(GatewayEvent):
    pass


@wraps_model(User)
class GuildBanRemove(GuildBanAdd):
    pass


class GuildEmojisUpdate(GatewayEvent):
    pass


class GuildIntegrationsUpdate(GatewayEvent):
    pass


class GuildMembersChunk(GatewayEvent):
    guild_id = snowflake
    members = listof(GuildMember)


@wraps_model(GuildMember, alias='member')
class GuildMemberAdd(GatewayEvent):
    pass


class GuildMemberRemove(GatewayEvent):
    guild_id = snowflake
    user = User


class GuildMemberUpdate(GatewayEvent):
    guild_id = snowflake
    user = User
    roles = listof(snowflake)


class GuildRoleCreate(GatewayEvent):
    guild_id = snowflake
    role = Role


class GuildRoleUpdate(GuildRoleCreate):
    pass


class GuildRoleDelete(GuildRoleCreate):
    pass


@wraps_model(Message)
class MessageCreate(GatewayEvent):
    @property
    def channel(self):
        return self.message.channel


@wraps_model(Message)
class MessageUpdate(MessageCreate):
    pass


class MessageDelete(GatewayEvent):
    id = snowflake
    channel_id = snowflake


class MessageDeleteBulk(GatewayEvent):
    channel_id = snowflake
    ids = listof(snowflake)


class PresenceUpdate(GatewayEvent):
    class Game(Model):
        # TODO enum
        type = int
        name = str
        url = str

    user = User
    guild_id = snowflake
    roles = listof(snowflake)
    game = Game
    status = str


class TypingStart(GatewayEvent):
    channel_id = snowflake
    user_id = snowflake
    timestamp = snowflake


@wraps_model(VoiceState, alias='state')
class VoiceStateUpdate(GatewayEvent):
    pass


class VoiceServerUpdate(GatewayEvent):
    token = str
    endpoint = str
    guild_id = snowflake
