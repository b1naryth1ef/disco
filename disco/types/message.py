import re

from holster.enum import Enum

from disco.types.base import SlottedModel, Field, snowflake, text, lazy_datetime, dictof, listof, enum
from disco.util.snowflake import to_snowflake
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


class MessageEmbedFooter(SlottedModel):
    text = Field(text)
    icon_url = Field(text)
    proxy_icon_url = Field(text)


class MessageEmbedImage(SlottedModel):
    url = Field(text)
    proxy_url = Field(text)
    width = Field(int)
    height = Field(int)


class MessageEmbedThumbnail(SlottedModel):
    url = Field(text)
    proxy_url = Field(text)
    width = Field(int)
    height = Field(int)


class MessageEmbedVideo(SlottedModel):
    url = Field(text)
    height = Field(int)
    width = Field(int)


class MessageEmbedAuthor(SlottedModel):
    name = Field(text)
    url = Field(text)
    icon_url = Field(text)
    icon_proxy_url = Field(text)


class MessageEmbedField(SlottedModel):
    name = Field(text)
    value = Field(text)
    inline = Field(bool)


class MessageEmbed(SlottedModel):
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
    title = Field(text)
    type = Field(str, default='rich')
    description = Field(text)
    url = Field(str)
    timestamp = Field(lazy_datetime)
    color = Field(int)
    footer = Field(MessageEmbedFooter)
    image = Field(MessageEmbedImage)
    thumbnail = Field(MessageEmbedThumbnail)
    video = Field(MessageEmbedVideo)
    author = Field(MessageEmbedAuthor)
    fields = Field(listof(MessageEmbedField))


class MessageAttachment(SlottedModel):
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
    id = Field(str)
    filename = Field(text)
    url = Field(str)
    proxy_url = Field(str)
    size = Field(int)
    height = Field(int)
    width = Field(int)


class Message(SlottedModel):
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
    id = Field(snowflake)
    channel_id = Field(snowflake)
    webhook_id = Field(snowflake)
    type = Field(enum(MessageType))
    author = Field(User)
    content = Field(text)
    nonce = Field(snowflake)
    timestamp = Field(lazy_datetime)
    edited_timestamp = Field(lazy_datetime)
    tts = Field(bool)
    mention_everyone = Field(bool)
    pinned = Field(bool)
    mentions = Field(dictof(User, key='id'))
    mention_roles = Field(listof(snowflake))
    embeds = Field(listof(MessageEmbed))
    attachments = Field(dictof(MessageAttachment, key='id'))

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
    def member(self):
        """
        Returns
        -------
        :class:`disco.types.guild.GuildMember`
            The guild member (if applicable) that sent this message.
        """
        return self.channel.guild.get_member(self.author)

    @cached_property
    def channel(self):
        """
        Returns
        -------
        :class:`disco.types.channel.Channel`
            The channel this message was created in.
        """
        return self.client.state.channels.get(self.channel_id)

    def pin(self):
        return self.channel.create_pin(self)

    def unpin(self):
        return self.channel.delete_pin(self)

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


class MessageTable(object):
    def __init__(self, sep=' | ', codeblock=True, header_break=True):
        self.header = []
        self.entries = []
        self.size_index = {}
        self.sep = sep
        self.codeblock = codeblock
        self.header_break = header_break

    def recalculate_size_index(self, cols):
        for idx, col in enumerate(cols):
            if idx not in self.size_index or len(col) > self.size_index[idx]:
                self.size_index[idx] = len(col)

    def set_header(self, *args):
        self.header = args
        self.recalculate_size_index(args)

    def add(self, *args):
        args = list(map(str, args))
        self.entries.append(args)
        self.recalculate_size_index(args)

    def compile_one(self, cols):
        data = self.sep.lstrip()

        for idx, col in enumerate(cols):
            padding = ' ' * ((self.size_index[idx] - len(col)))
            data += col + padding + self.sep

        return data.rstrip()

    def compile(self):
        data = []
        data.append(self.compile_one(self.header))

        if self.header_break:
            data.append('-' * (sum(self.size_index.values()) + (len(self.header) * len(self.sep)) + 1))

        for row in self.entries:
            data.append(self.compile_one(row))

        if self.codeblock:
            return '```' + '\n'.join(data) + '```'

        return '\n'.join(data)
