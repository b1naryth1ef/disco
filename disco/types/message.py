import re
import skema

from disco.util.cache import cached_property
from disco.util.types import PreHookType, ListToDictType
from disco.types.base import BaseType
from disco.types.user import User
from disco.types.guild import Role


class MessageEmbed(BaseType):
    title = skema.StringType()
    type = skema.StringType()
    description = skema.StringType()
    url = skema.StringType()


class MessageAttachment(BaseType):
    id = skema.SnowflakeType()
    filename = skema.StringType()
    url = skema.StringType()
    proxy_url = skema.StringType()
    size = skema.IntType()
    height = skema.IntType()
    width = skema.IntType()


class Message(BaseType):
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

    mentions = ListToDictType('id', skema.ModelType(User))
    mention_roles = skema.ListType(skema.SnowflakeType())

    embeds = skema.ListType(skema.ModelType(MessageEmbed))
    attachments = ListToDictType('id', skema.ModelType(MessageAttachment))

    @cached_property
    def guild(self):
        return self.channel.guild

    @cached_property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    def reply(self, *args, **kwargs):
        return self.channel.send_message(*args, **kwargs)

    def edit(self, content):
        return self.client.api.channels_messages_modify(self.channel_id, self.id, content)

    def delete(self, content):
        return self.client.api.channels_messages_delete(self.channel_id, self.id)

    def is_mentioned(self, entity):
        if isinstance(entity, User):
            return entity.id in self.mentions
        elif isinstance(entity, Role):
            return entity.id in self.mention_roles
        elif isinstance(entity, long):
            return entity in self.mentions or entity in self.mention_roles
        else:
            raise Exception('Unknown entity: {} ({})'.format(entity, type(entity)))

    @cached_property
    def without_mentions(self):
        return self.replace_mentions(
            lambda u: '',
            lambda r: '')

    def replace_mentions(self, user_replace, role_replace):
        if not self.mentions and not self.mention_roles:
            return

        def replace(match):
            id = match.group(0)
            if id in self.mention_roles:
                return role_replace(id)
            else:
                return user_replace(self.mentions.get(id))

        return re.sub('<@!?([0-9]+)>', replace, self.content)
