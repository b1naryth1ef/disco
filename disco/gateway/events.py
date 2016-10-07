import inflection
import skema
import six

from disco.util import skema_find_recursive_by_type
from disco.types import Guild, Channel, User, GuildMember, Role, Message, VoiceState


# TODO: clean this... use BaseType, etc
class GatewayEvent(skema.Model):
    @staticmethod
    def from_dispatch(client, data):
        cls = globals().get(inflection.camelize(data['t'].lower()))
        if not cls:
            raise Exception('Could not find cls for {}'.format(data['t']))

        obj = cls.create(data['d'])

        for field, value in skema_find_recursive_by_type(obj, skema.ModelType):
            value.client = client

        return obj

    @classmethod
    def create(cls, obj):
        # If this event is wrapping a model, pull its fields
        if hasattr(cls, '_wraps_model'):
            alias, model = cls._wraps_model

            data = {
                k: obj.pop(k) for k in six.iterkeys(model._fields_by_stored_name) if k in obj
            }

            obj[alias] = data

        self = cls(obj)
        self.validate()
        return self


def wraps_model(model, alias=None):
    alias = alias or model.__name__.lower()

    def deco(cls):
        cls.add_field(alias, skema.ModelType(model))
        cls._wraps_model = (alias, model)
        return cls
    return deco


class Ready(GatewayEvent):
    version = skema.IntType(stored_name='v')
    session_id = skema.StringType()
    user = skema.ModelType(User)
    guilds = skema.ListType(skema.ModelType(Guild))


class Resumed(GatewayEvent):
    pass


@wraps_model(Guild)
class GuildCreate(GatewayEvent):
    unavailable = skema.BooleanType(default=None)


@wraps_model(Guild)
class GuildUpdate(GatewayEvent):
    guild = skema.ModelType(Guild)


class GuildDelete(GatewayEvent):
    id = skema.SnowflakeType()
    unavailable = skema.BooleanType(default=None)


@wraps_model(Channel)
class ChannelCreate(GatewayEvent):
    @property
    def guild(self):
        return self.channel.guild


class ChannelUpdate(ChannelCreate):
    pass


class ChannelDelete(ChannelCreate):
    pass


class ChannelPinsUpdate(GatewayEvent):
    channel_id = skema.SnowflakeType()
    last_pin_timestamp = skema.IntType()


@wraps_model(User)
class GuildBanAdd(GatewayEvent):
    pass


class GuildBanRemove(GuildBanAdd):
    pass


class GuildEmojisUpdate(GatewayEvent):
    pass


class GuildIntegrationsUpdate(GatewayEvent):
    pass


class GuildMembersChunk(GatewayEvent):
    guild_id = skema.SnowflakeType()
    members = skema.ListType(skema.ModelType(GuildMember))


@wraps_model(GuildMember, alias='member')
class GuildMemberAdd(GatewayEvent):
    pass


class GuildMemberRemove(GatewayEvent):
    guild_id = skema.SnowflakeType()
    user = skema.ModelType(User)


class GuildMemberUpdate(GatewayEvent):
    guild_id = skema.SnowflakeType()
    user = skema.ModelType(User)
    roles = skema.ListType(skema.SnowflakeType())


class GuildRoleCreate(GatewayEvent):
    guild_id = skema.SnowflakeType()
    role = skema.ModelType(Role)


class GuildRoleUpdate(GatewayEvent):
    guild_id = skema.SnowflakeType()
    role = skema.ModelType(Role)


class GuildRoleDelete(GatewayEvent):
    guild_id = skema.SnowflakeType()
    role = skema.ModelType(Role)


@wraps_model(Message)
class MessageCreate(GatewayEvent):
    @property
    def channel(self):
        return self.message.channel


class MessageUpdate(MessageCreate):
    pass


class MessageDelete(GatewayEvent):
    id = skema.SnowflakeType()
    channel_id = skema.SnowflakeType()


class MessageDeleteBulk(GatewayEvent):
    channel_id = skema.SnowflakeType()
    ids = skema.ListType(skema.SnowflakeType())


class PresenceUpdate(GatewayEvent):
    class Game(skema.Model):
        type = skema.IntType()
        name = skema.StringType()
        url = skema.StringType(required=False)

    user = skema.ModelType(User)
    guild_id = skema.SnowflakeType()
    roles = skema.ListType(skema.SnowflakeType())
    game = skema.ModelType(Game)
    status = skema.StringType()


class TypingStart(GatewayEvent):
    channel_id = skema.SnowflakeType()
    user_id = skema.SnowflakeType()
    timestamp = skema.IntType()


@wraps_model(VoiceState, alias='state')
class VoiceStateUpdate(GatewayEvent):
    pass


class VoiceServerUpdate(GatewayEvent):
    token = skema.StringType()
    endpoint = skema.StringType()
    guild_id = skema.SnowflakeType()
