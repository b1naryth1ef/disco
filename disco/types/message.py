import re
import six
import warnings
import functools

from holster.enum import Enum

from disco.types.base import (
    SlottedModel, Field, ListField, AutoDictField, snowflake, text,
    datetime, enum
)
from disco.util.paginator import Paginator
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


class Emoji(SlottedModel):
    id = Field(snowflake)
    name = Field(text)

    @cached_property
    def custom(self):
        return self.id is not None

    def __eq__(self, other):
        if isinstance(other, Emoji):
            return self.id == other.id and self.name == other.name
        raise NotImplementedError

    def to_string(self):
        if self.id:
            return '{}:{}'.format(self.name, self.id)
        return self.name


class MessageReactionEmoji(Emoji):
    pass


class MessageReaction(SlottedModel):
    emoji = Field(MessageReactionEmoji)
    count = Field(int)
    me = Field(bool)


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
    Message embed object.

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
    url = Field(text)
    timestamp = Field(datetime)
    color = Field(int)
    footer = Field(MessageEmbedFooter)
    image = Field(MessageEmbedImage)
    thumbnail = Field(MessageEmbedThumbnail)
    video = Field(MessageEmbedVideo)
    author = Field(MessageEmbedAuthor)
    fields = ListField(MessageEmbedField)

    def set_footer(self, *args, **kwargs):
        self.footer = MessageEmbedFooter(*args, **kwargs)

    def set_image(self, *args, **kwargs):
        self.image = MessageEmbedImage(*args, **kwargs)

    def set_thumbnail(self, *args, **kwargs):
        self.thumbnail = MessageEmbedThumbnail(*args, **kwargs)

    def set_video(self, *args, **kwargs):
        self.video = MessageEmbedVideo(*args, **kwargs)

    def set_author(self, *args, **kwargs):
        self.author = MessageEmbedAuthor(*args, **kwargs)

    def add_field(self, *args, **kwargs):
        self.fields.append(MessageEmbedField(*args, **kwargs))


class MessageAttachment(SlottedModel):
    """
    Message attachment object.

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
    url = Field(text)
    proxy_url = Field(text)
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
    timestamp = Field(datetime)
    edited_timestamp = Field(datetime)
    tts = Field(bool)
    mention_everyone = Field(bool)
    pinned = Field(bool)
    mentions = AutoDictField(User, 'id')
    mention_roles = ListField(snowflake)
    embeds = ListField(MessageEmbed)
    attachments = AutoDictField(MessageAttachment, 'id')
    reactions = ListField(MessageReaction)

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
        :func:`disco.types.channel.Channel.send_message`).

        Returns
        -------
        :class:`Message`
            The created message object.
        """
        return self.channel.send_message(*args, **kwargs)

    def edit(self, *args, **kwargs):
        """
        Edit this message.

        Args
        ----
        content : str
            The new edited contents of the message.

        Returns
        -------
        :class:`Message`
            The edited message object.
        """
        return self.client.api.channels_messages_modify(self.channel_id, self.id, *args, **kwargs)

    def delete(self):
        """
        Delete this message.

        Returns
        -------
        :class:`Message`
            The deleted message object.
        """
        return self.client.api.channels_messages_delete(self.channel_id, self.id)

    def get_reactors(self, emoji, *args, **kwargs):
        """
        Returns an iterator which paginates the reactors for the given emoji.

        Returns
        -------
        Paginator(`User`)
            An iterator which handles pagination of reactors.
        """
        if isinstance(emoji, Emoji):
            emoji = emoji.to_string()

        return Paginator(
            self.client.api.channels_messages_reactions_get,
            'after',
            self.channel_id,
            self.id,
            emoji,
            *args,
            **kwargs)

    def create_reaction(self, emoji):
        warnings.warn(
            'Message.create_reaction will be deprecated soon, use Message.add_reaction',
            DeprecationWarning)
        return self.add_reaction(emoji)

    def add_reaction(self, emoji):
        """
        Adds a reaction to the message.

        Parameters
        ----------
        emoji : Emoji|str
            An emoji or string representing an emoji
        """
        if isinstance(emoji, Emoji):
            emoji = emoji.to_string()

        self.client.api.channels_messages_reactions_create(
            self.channel_id,
            self.id,
            emoji)

    def delete_reaction(self, emoji, user=None):
        if isinstance(emoji, Emoji):
            emoji = emoji.to_string()

        if user:
            user = to_snowflake(user)

        self.client.api.channels_messages_reactions_delete(
            self.channel_id,
            self.id,
            emoji,
            user)

    def is_mentioned(self, entity):
        """
        Returns
        -------
        bool
            Whether the give entity was mentioned.
        """
        entity = to_snowflake(entity)
        return entity in self.mentions or entity in self.mention_roles

    @cached_property
    def without_mentions(self, valid_only=False):
        """
        Returns
        -------
        str
            the message contents with all mentions removed.
        """
        return self.replace_mentions(
            lambda u: '',
            lambda r: '',
            lambda c: '',
            nonexistant=not valid_only)

    @cached_property
    def with_proper_mentions(self):
        def replace_user(u):
            return u'@' + six.text_type(u)

        def replace_role(r):
            return u'@' + six.text_type(r)

        def replace_channel(c):
            return six.text_type(c)

        return self.replace_mentions(replace_user, replace_role, replace_channel)

    def replace_mentions(self, user_replace=None, role_replace=None, channel_replace=None, nonexistant=False):
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
        def replace(getter, func, match):
            oid = int(match.group(2))
            obj = getter(oid)

            if obj or nonexistant:
                return func(obj or oid) or match.group(0)

            return match.group(0)

        content = self.content

        if user_replace:
            replace_user = functools.partial(replace, self.mentions.get, user_replace)
            content = re.sub('(<@!?([0-9]+)>)', replace_user, content)

        if role_replace:
            replace_role = functools.partial(replace, lambda v: (self.guild and self.guild.roles.get(v)), role_replace)
            content = re.sub('(<@&([0-9]+)>)', replace_role, content)

        if channel_replace:
            replace_channel = functools.partial(replace, self.client.state.channels.get, channel_replace)
            content = re.sub('(<#([0-9]+)>)', replace_channel, content)

        return content


class Sendable(object):
    """
    Base class which implements an entity that can be sent as a message to Discord.
    """

    def compile(self):
        """
        Should return a valid (e.g. properly sized, < 2000 length) message that
        can be sent to Discord.
        """

    @staticmethod
    def fit(contents, head='```', tail='```', length=2000):
        contents = Sendable.truncate(contents, tail='', length=length - (len(head) + len(tail)))
        return u'{}{}{}'.format(head, contents, tail)

    @staticmethod
    def truncate(contents, tail='...', length=2000):
        if len(contents) <= length:
            return contents

        to_truncate = len(contents) - length + len(tail)
        return contents[:-to_truncate] + tail
