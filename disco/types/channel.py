import skema

from holster.enum import Enum

# from disco.types.guild import Guild
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


class PermissionOverwrite(skema.Model):
    id = skema.SnowflakeType()
    type = skema.StringType(choices=PermissionOverwriteType.ALL_VALUES)

    allow = skema.IntType()
    deny = skema.IntType()


class Channel(skema.Model):
    id = skema.SnowflakeType()

    name = skema.StringType()
    topic = skema.StringType()
    last_message_id = skema.SnowflakeType()
    position = skema.IntType()
    bitrate = skema.IntType(required=False)

    recipient = skema.ModelType(User, required=False)
    type = skema.IntType(choices=ChannelType.ALL_VALUES)

    permission_overwrites = skema.ListType(skema.ModelType(PermissionOverwrite))
