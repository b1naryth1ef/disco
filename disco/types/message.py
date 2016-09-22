import skema

from disco.util.types import PreHookType
from disco.types.user import User


class MessageEmbed(skema.Model):
    title = skema.StringType()
    type = skema.StringType()
    description = skema.StringType()
    url = skema.StringType()


class MessageAttachment(skema.Model):
    id = skema.SnowflakeType()
    filename = skema.StringType()
    url = skema.StringType()
    proxy_url = skema.StringType()
    size = skema.IntType()
    height = skema.IntType()
    width = skema.IntType()


class Message(skema.Model):
    id = skema.SnowflakeType()
    channel_id = skema.SnowflakeType()

    author = skema.ModelType(User)
    content = skema.StringType()
    nonce = skema.StringType()

    timestamp = PreHookType(lambda k: k[:-6], skema.DateTimeType())
    edited_timestamp = PreHookType(lambda k: k[:-6], skema.DateTimeType())

    tts = skema.BooleanType()
    mention_everyone = skema.BooleanType()

    pinned = skema.BooleanType(required=False)

    mentions = skema.ListType(skema.ModelType(User))
    mention_roles = skema.ListType(skema.SnowflakeType())

    embeds = skema.ListType(skema.ModelType(MessageEmbed))
    attachment = skema.ListType(skema.ModelType(MessageAttachment))
