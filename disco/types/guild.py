import skema
import copy

from disco.api.http import APIException
from disco.util import to_snowflake
from disco.types.base import BaseType
from disco.util.types import PreHookType, ListToDictType
from disco.types.user import User
from disco.types.voice import VoiceState
from disco.types.permissions import PermissionType
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
    permissions = PermissionType()
    position = skema.IntType()


class GuildMember(BaseType):
    user = skema.ModelType(User)
    guild_id = skema.SnowflakeType(required=False)
    mute = skema.BooleanType()
    deaf = skema.BooleanType()
    joined_at = PreHookType(lambda k: k[:-6], skema.DateTimeType())
    roles = skema.ListType(skema.SnowflakeType())

    def get_voice_state(self):
        return self.guild.get_voice_state(self)

    def kick(self):
        self.client.api.guilds_members_kick(self.guild.id, self.user.id)

    def ban(self, delete_message_days=0):
        self.client.api.guilds_bans_create(self.guild.id, self.user.id, delete_message_days)

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

    members = ListToDictType('id', skema.ModelType(copy.deepcopy(GuildMember)))
    channels = ListToDictType('id', skema.ModelType(Channel))
    roles = ListToDictType('id', skema.ModelType(Role))
    emojis = ListToDictType('id', skema.ModelType(Emoji))
    voice_states = ListToDictType('session_id', skema.ModelType(VoiceState))

    def get_voice_state(self, user):
        user = to_snowflake(user)

        for state in self.voice_states.values():
            if state.user_id == user:
                return state

    def get_member(self, user):
        user = to_snowflake(user)

        if user not in self.members:
            try:
                self.members[user] = self.client.api.guilds_members_get(self.id, user)
            except APIException:
                pass

        return self.members.get(user)

    def validate_members(self, ctx):
        if self.members:
            for member in self.members.values():
                member.guild = self
                member.guild_id = self.id

    def validate_channels(self, ctx):
        if self.channels:
            for channel in self.channels.values():
                channel.guild_id = self.id
                channel.guild = self
