import skema

from disco.util.cache import cached_property
from disco.types.base import BaseType
from disco.util.types import PreHookType
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

    members = skema.ListType(skema.ModelType(GuildMember))
    voice_states = skema.ListType(skema.ModelType(VoiceState))
    channels = skema.ListType(skema.ModelType(Channel))
    roles = skema.ListType(skema.ModelType(Role))
    emojis = skema.ListType(skema.ModelType(Emoji))

    @cached_property
    def members_dict(self):
        return {i.user.id: i for i in self.members}

    def get_member(self, user):
        return self.members_dict.get(user.id)

    def validate_channels(self, ctx):
        if self.channels:
            for channel in self.channels:
                channel.guild_id = self.id
