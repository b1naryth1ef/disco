import skema

from holster.enum import Enum

from disco.util.cache import cached_property
from disco.types.base import BaseType
from disco.types.user import User


ChannelType = Enum(
    GUILD_TEXT=0,
    DM=1,
    GUILD_VOICE=2,
    GROUP_DM=3,
)

PermissionOverwriteType = Enum(
    ROLE='role',
    MEMBER='member'
)


class PermissionOverwrite(BaseType):
    id = skema.SnowflakeType()
    type = skema.StringType(choices=PermissionOverwriteType.ALL_VALUES)

    allow = skema.IntType()
    deny = skema.IntType()


class Channel(BaseType):
    id = skema.SnowflakeType()
    guild_id = skema.SnowflakeType(required=False)

    name = skema.StringType()
    topic = skema.StringType()
    last_message_id = skema.SnowflakeType()
    position = skema.IntType()
    bitrate = skema.IntType(required=False)

    recipient = skema.ModelType(User, required=False)
    type = skema.IntType(choices=ChannelType.ALL_VALUES)

    permission_overwrites = skema.ListType(skema.ModelType(PermissionOverwrite))

    @cached_property
    def guild(self):
        print self.guild_id
        print self.client.state.guilds
        return self.client.state.guilds.get(self.guild_id)
