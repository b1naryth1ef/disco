import inflection
import skema

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
        self = cls(obj)
        self.validate()
        return self


def Sub(field):
    class _T(GatewayEvent):
        @classmethod
        def create(cls, obj):
            obj[field] = obj
            self = cls(obj)
            self.validate()
            return self

    return _T


class Ready(GatewayEvent):
    version = skema.IntType(stored_name='v')
    session_id = skema.StringType()
    user = skema.ModelType(User)
    guilds = skema.ListType(skema.ModelType(Guild))


class Resumed(GatewayEvent):
    pass


class GuildCreate(Sub('guild')):
    guild = skema.ModelType(Guild)
    unavailable = skema.BooleanType(default=None)


class GuildUpdate(Sub('guild')):
    guild = skema.ModelType(Guild)


class GuildDelete(GatewayEvent):
    id = skema.SnowflakeType()
    unavailable = skema.BooleanType(default=None)


class ChannelCreate(Sub('channel')):
    channel = skema.ModelType(Channel)

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


class GuildBanAdd(Sub('user')):
    user = skema.ModelType(User)


class GuildBanRemove(Sub('user')):
    user = skema.ModelType(User)


class GuildEmojisUpdate(GatewayEvent):
    pass


class GuildIntegrationsUpdate(GatewayEvent):
    pass


class GuildMembersChunk(GatewayEvent):
    guild_id = skema.SnowflakeType()
    members = skema.ListType(skema.ModelType(GuildMember))


class GuildMemberAdd(Sub('member')):
    member = skema.ModelType(GuildMember)


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


class MessageCreate(Sub('message')):
    message = skema.ModelType(Message)

    @property
    def channel(self):
        return self.message.channel


class MessageUpdate(MessageCreate):
    message = skema.ModelType(Message)


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


class VoiceStateUpdate(Sub('state')):
    state = skema.ModelType(VoiceState)


class VoiceServerUpdate(GatewayEvent):
    token = skema.StringType()
    endpoint = skema.StringType()
    guild_id = skema.SnowflakeType()
