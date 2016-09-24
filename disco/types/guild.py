import skema

from disco.types.base import BaseType
from disco.util.types import PreHookType, ListToDictType
from disco.types.user import User
from disco.types.voice import VoiceState
from disco.types.channel import Channel


class Emoji(BaseType):
    id = skema.SnowflakeType()
    name = skema.StringType()
    require_colons = skema.BooleanType()
    managed = skema.BooleanType()
    roles = skema.ListType(skema.SnowflakeType())


class Role(BaseType):
    id = skema.SnowflakeType()
    name = skema.StringType()
    hoist = skema.BooleanType()
    managed = skema.BooleanType()
    color = skema.IntType()
    permissions = skema.IntType()
    position = skema.IntType()


class GuildMember(BaseType):
    user = skema.ModelType(User)
    mute = skema.BooleanType()
    deaf = skema.BooleanType()
    joined_at = PreHookType(lambda k: k[:-6], skema.DateTimeType())
    roles = skema.ListType(skema.SnowflakeType())

    @property
    def id(self):
        return self.user.id


class Guild(BaseType):
    id = skema.SnowflakeType()

    owner_id = skema.SnowflakeType()
    afk_channel_id = skema.SnowflakeType()
    embed_channel_id = skema.SnowflakeType()

    name = skema.StringType()
    icon = skema.BinaryType(None)
    splash = skema.BinaryType(None)
    region = skema.StringType()

    afk_timeout = skema.IntType()
    embed_enabled = skema.BooleanType()
    verification_level = skema.IntType()
    mfa_level = skema.IntType()

    features = skema.ListType(skema.StringType())

    members = ListToDictType('id', skema.ModelType(GuildMember))
    channels = ListToDictType('id', skema.ModelType(Channel))
    roles = ListToDictType('id', skema.ModelType(Role))
    emojis = ListToDictType('id', skema.ModelType(Emoji))
    voice_states = ListToDictType('id', skema.ModelType(VoiceState))

    def get_member(self, user):
        return self.members.get(user.id)

    def validate_channels(self, ctx):
        if self.channels:
            for channel in self.channels.values():
                channel.guild_id = self.id
