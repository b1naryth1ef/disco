import inflection
import skema

from disco.types import Guild, Channel, User, GuildMember, Role, Message, VoiceState


class GatewayEvent(skema.Model):
    @staticmethod
    def from_dispatch(obj):
        cls = globals().get(inflection.camelize(obj['t'].lower()))
        if not cls:
            raise Exception('Could not find cls for {}'.format(obj['t']))

        return cls, cls.create(obj['d'])

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


class ChannelUpdate(Sub('channel')):
    channel = skema.ModelType(Channel)


class ChannelDelete(Sub('channel')):
    channel = skema.ModelType(Channel)


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


class MessageUpdate(Sub('message')):
    message = skema.ModelType(Message)


class MessageDelete(GatewayEvent):
    id = skema.SnowflakeType()
    channel_id = skema.SnowflakeType()


class MessageDeleteBulk(GatewayEvent):
    channel_id = skema.SnowflakeType()
    ids = skema.ListType(skema.SnowflakeType())


class PresenceUpdate(GatewayEvent):
    user = skema.ModelType(User)
    guild_id = skema.SnowflakeType()
    roles = skema.ListType(skema.SnowflakeType())
    game = skema.StringType()
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
