import re
import skema

from disco.util import to_snowflake
from disco.util.functional import cached_property
from disco.util.types import PreHookType, ListToDictType
from disco.types.base import BaseType
from disco.types.user import User


class MessageEmbed(BaseType):
    """
    Message embed object

    Attributes
    ----------
    title : str
        Title of the embed.
    type : str
        Type of the embed.
    description : str
        Description of the embed.
    url : str
        URL of the embed.
    """
    title = skema.StringType()
    type = skema.StringType()
    description = skema.StringType()
    url = skema.StringType()


class MessageAttachment(BaseType):
    """
    Message attachment object

    Attributes
    ----------
    id : snowflake
        The id of this attachment.
    filename : str
        The filename of this attachment.
    url : str
        The URL of this attachment.
    proxy_url : str
        The URL to proxy through when downloading the attachment.
    size : int
        Size of the attachment.
    height : int
        Height of the attachment.
    width : int
        Width of the attachment.
    """
    id = skema.SnowflakeType()
    filename = skema.StringType()
    url = skema.StringType()
    proxy_url = skema.StringType()
    size = skema.IntType()
    height = skema.IntType()
    width = skema.IntType()


class Message(BaseType):
    """
    Represents a Message created within a Channel on Discord.

    Attributes
    ----------
    id : snowflake
        The ID of this message.
    channel_id : snowflake
        The channel ID this message was sent in.
    author : :class:`disco.types.user.User`
        The author of this message.
    content : str
        The unicode contents of this message.
    nonce : str
        The nonce of this message.
    timestamp : datetime
        When this message was created.
    edited_timestamp : Optional[datetime]
        When this message was last edited.
    tts : bool
        Whether this is a TTS (text-to-speech) message.
    mention_everyone : bool
        Whether this message has an @everyone which mentions everyone.
    pinned : bool
        Whether this message is pinned in the channel.
    mentions : dict(snowflake, :class:`disco.types.user.User`)
        All users mentioned within this message.
    mention_roles : list(snowflake)
        All roles mentioned within this message.
    embeds : list(:class:`MessageEmbed`)
        All embeds for this message.
    attachments : list(:class:`MessageAttachment`)
        All attachments for this message.
    """
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

    def __str__(self):
        return '<Message {} ({})>'.format(self.id, self.channel_id)

    @cached_property
    def guild(self):
        """
        Returns
        -------
        :class:`disco.types.guild.Guild`
            The guild (if applicable) this message was created in.
        """
        return self.channel.guild

    @cached_property
    def channel(self):
        """
        Returns
        -------
        :class:`disco.types.channel.Channel`
            The channel this message was created in.
        """
        return self.client.state.channels.get(self.channel_id)

    def reply(self, *args, **kwargs):
        """
        Reply to this message (proxys arguments to
        :func:`disco.types.channel.Channel.send_message`)

        Returns
        -------
        :class:`Message`
            The created message object.
        """
        return self.channel.send_message(*args, **kwargs)

    def edit(self, content):
        """
        Edit this message

        Args
        ----
        content : str
            The new edited contents of the message.

        Returns
        -------
        :class:`Message`
            The edited message object.
        """
        return self.client.api.channels_messages_modify(self.channel_id, self.id, content)

    def delete(self):
        """
        Delete this message.

        Returns
        -------
        :class:`Message`
            The deleted message object.
        """
        return self.client.api.channels_messages_delete(self.channel_id, self.id)

    def is_mentioned(self, entity):
        """
        Returns
        -------
        bool
            Whether the give entity was mentioned.
        """
        id = to_snowflake(entity)
        return id in self.mentions or id in self.mention_roles

    @cached_property
    def without_mentions(self):
        """
        Returns
        -------
        str
            the message contents with all valid mentions removed.
        """
        return self.replace_mentions(
            lambda u: '',
            lambda r: '')

    def replace_mentions(self, user_replace, role_replace):
        """
        Replaces user and role mentions with the result of a given lambda/function.

        Args
        ----
        user_replace : function
            A function taking a single argument, the user object mentioned, and
            returning a valid string.
        role_replace : function
            A function taking a single argument, the role ID mentioned, and
            returning a valid string.

        Returns
        -------
        str
            The message contents with all valid mentions replaced.
        """
        if not self.mentions and not self.mention_roles:
            return

        def replace(match):
            id = match.group(0)
            if id in self.mention_roles:
                return role_replace(id)
            else:
                return user_replace(self.mentions.get(id))

        return re.sub('<@!?([0-9]+)>', replace, self.content)
