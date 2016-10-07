import re

from holster.enum import Enum

from disco.types.base import Model, snowflake, text, datetime, dictof, listof, enum
from disco.util import to_snowflake
from disco.util.functional import cached_property
from disco.types.user import User


MessageType = Enum(
    DEFAULT=0,
    RECIPIENT_ADD=1,
    RECIPIENT_REMOVE=2,
    CALL=3,
    CHANNEL_NAME_CHANGE=4,
    CHANNEL_ICON_CHANGE=5,
    PINS_ADD=6
)


class MessageEmbed(Model):
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
    title = text
    type = str
    description = text
    url = str


class MessageAttachment(Model):
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
    id = str
    filename = text
    url = str
    proxy_url = str
    size = int
    height = int
    width = int


class Message(Model):
    """
    Represents a Message created within a Channel on Discord.

    Attributes
    ----------
    id : snowflake
        The ID of this message.
    channel_id : snowflake
        The channel ID this message was sent in.
    type : ``MessageType``
        Type of the message.
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
    id = snowflake
    channel_id = snowflake
    type = enum(MessageType)
    author = User
    content = text
    nonce = snowflake
    timestamp = datetime
    edited_timestamp = datetime
    tts = bool
    mention_everyone = bool
    pinned = bool
    mentions = dictof(User, key='id')
    mention_roles = listof(snowflake)
    embeds = listof(MessageEmbed)
    attachments = dictof(MessageAttachment, key='id')

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
