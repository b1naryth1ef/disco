import re
import six

from six.moves import map
from holster.enum import Enum

from disco.util.snowflake import to_snowflake
from disco.util.functional import one_or_many, chunks
from disco.types.user import User
from disco.types.base import SlottedModel, Field, AutoDictField, snowflake, enum, text, cached_property
from disco.types.permissions import Permissions, Permissible, PermissionValue


NSFW_RE = re.compile('^nsfw(-|$)')


ChannelType = Enum(
    GUILD_TEXT=0,
    DM=1,
    GUILD_VOICE=2,
    GROUP_DM=3,
    GUILD_CATEGORY=4,
)

PermissionOverwriteType = Enum(
    ROLE='role',
    MEMBER='member',
)


class ChannelSubType(SlottedModel):
    channel_id = Field(None)

    @cached_property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)


class PermissionOverwrite(ChannelSubType):
    """
    A PermissionOverwrite for a :class:`Channel`.

    Attributes
    ----------
    id : snowflake
        The overwrite ID
    type : :const:`disco.types.channel.PermissionsOverwriteType`
        The overwrite type
    allowed : :class:`PermissionValue`
        All allowed permissions
    denied : :class:`PermissionValue`
        All denied permissions
    """
    id = Field(snowflake)
    type = Field(enum(PermissionOverwriteType))
    allow = Field(PermissionValue, cast=int)
    deny = Field(PermissionValue, cast=int)

    channel_id = Field(snowflake)

    @classmethod
    def create_for_channel(cls, channel, entity, allow=0, deny=0):
        from disco.types.guild import Role

        ptype = PermissionOverwriteType.ROLE if isinstance(entity, Role) else PermissionOverwriteType.MEMBER
        return cls(
            client=channel.client,
            id=entity.id,
            type=ptype,
            allow=allow,
            deny=deny,
            channel_id=channel.id,
        ).save()

    @property
    def compiled(self):
        value = PermissionValue()
        value -= self.deny
        value += self.allow
        return value

    def save(self, **kwargs):
        self.client.api.channels_permissions_modify(self.channel_id,
                                                    self.id,
                                                    self.allow.value or 0,
                                                    self.deny.value or 0,
                                                    self.type.name,
                                                    **kwargs)
        return self

    def delete(self, **kwargs):
        self.client.api.channels_permissions_delete(self.channel_id, self.id, **kwargs)


class Channel(SlottedModel, Permissible):
    """
    Represents a Discord Channel.

    Attributes
    ----------
    id : snowflake
        The channel ID.
    guild_id : Optional[snowflake]
        The guild id this channel is part of.
    name : str
        The channel's name.
    topic : str
        The channel's topic.
    position : int
        The channel's position.
    bitrate : int
        The channel's bitrate.
    user_limit : int
        The channel's user limit.
    recipients: list(:class:`disco.types.user.User`)
        Members of this channel (if this is a DM channel).
    type : :const:`ChannelType`
        The type of this channel.
    overwrites : dict(snowflake, :class:`disco.types.channel.PermissionOverwrite`)
        Channel permissions overwrites.
    """
    id = Field(snowflake)
    guild_id = Field(snowflake)
    name = Field(text)
    topic = Field(text)
    last_message_id = Field(snowflake)
    position = Field(int)
    bitrate = Field(int)
    user_limit = Field(int)
    recipients = AutoDictField(User, 'id')
    nsfw = Field(bool)
    type = Field(enum(ChannelType))
    overwrites = AutoDictField(PermissionOverwrite, 'id', alias='permission_overwrites')
    parent_id = Field(snowflake)

    def __init__(self, *args, **kwargs):
        super(Channel, self).__init__(*args, **kwargs)
        self.after_load()

    def after_load(self):
        # TODO: hackfix
        self.attach(six.itervalues(self.overwrites), {'channel_id': self.id, 'channel': self})

    def __str__(self):
        return u'#{}'.format(self.name) if self.name else six.text_type(self.id)

    def __repr__(self):
        return u'<Channel {} ({})>'.format(self.id, self)

    def get_permissions(self, user):
        """
        Get the permissions a user has in the channel.

        Returns
        -------
        :class:`disco.types.permissions.PermissionValue`
            Computed permission value for the user.
        """
        if not self.guild_id:
            return Permissions.ADMINISTRATOR

        member = self.guild.get_member(user)
        base = self.guild.get_permissions(member)

        # First grab and apply the everyone overwrite
        everyone = self.overwrites.get(self.guild_id)
        if everyone:
            base -= everyone.deny
            base += everyone.allow

        denies = 0
        allows = 0
        for role_id in member.roles:
            overwrite = self.overwrites.get(role_id)
            if overwrite:
                denies |= overwrite.deny
                allows |= overwrite.allow

        base -= denies
        base += allows

        ow_member = self.overwrites.get(member.user.id)
        if ow_member:
            base -= ow_member.deny
            base += ow_member.allow

        return base

    @property
    def mention(self):
        return '<#{}>'.format(self.id)

    @property
    def is_guild(self):
        """
        Whether this channel belongs to a guild.
        """
        return self.type in (ChannelType.GUILD_TEXT, ChannelType.GUILD_VOICE, ChannelType.GUILD_CATEGORY)

    @property
    def is_dm(self):
        """
        Whether this channel is a DM (does not belong to a guild).
        """
        return self.type in (ChannelType.DM, ChannelType.GROUP_DM)

    @property
    def is_nsfw(self):
        """
        Whether this channel is an NSFW channel.
        """
        return bool(self.type == ChannelType.GUILD_TEXT and (self.nsfw or NSFW_RE.match(self.name)))

    @property
    def is_voice(self):
        """
        Whether this channel supports voice.
        """
        return self.type in (ChannelType.GUILD_VOICE, ChannelType.GROUP_DM)

    @property
    def messages(self):
        """
        A default `MessageIterator` for the channel, can be used to quickly and
        easily iterate over the channels entire message history. For more control,
        use `Channel.messages_iter`.
        """
        return self.messages_iter()

    @cached_property
    def guild(self):
        """
        Guild this channel belongs to (or None if not applicable).
        """
        return self.client.state.guilds.get(self.guild_id)

    @cached_property
    def parent(self):
        """
        Parent this channel belongs to (or None if not applicable).
        """
        return self.guild.channels.get(self.parent_id)

    def messages_iter(self, **kwargs):
        """
        Creates a new `MessageIterator` for the channel with the given keyword
        arguments.
        """
        return MessageIterator(self.client, self, **kwargs)

    def get_message(self, message):
        """
        Attempts to fetch and return a `Message` from the message object
        or id.

        Returns
        -------
        `Message`
            The fetched message
        """
        return self.client.api.channels_messages_get(self.id, to_snowflake(message))

    def get_invites(self):
        """
        Returns
        -------
        list(`Invite`)
            Returns a list of all invites for this channel.
        """
        return self.client.api.channels_invites_list(self.id)

    def create_invite(self, *args, **kwargs):
        """
        Attempts to create a new invite with the given arguments. For more
        information see `Invite.create_for_channel`.

        Returns
        -------
        `Invite`
        """

        from disco.types.invite import Invite
        return Invite.create_for_channel(self, *args, **kwargs)

    def get_pins(self):
        """
        Returns
        -------
        list(`Message`)
            Returns a list of all pinned messages for this channel.
        """
        return self.client.api.channels_pins_list(self.id)

    def create_pin(self, message):
        """
        Pins the given message to the channel.

        Params
        ------
        message : `Message`|snowflake
            The message or message ID to pin.
        """
        self.client.api.channels_pins_create(self.id, to_snowflake(message))

    def delete_pin(self, message):
        """
        Unpins the given message from the channel.

        Params
        ------
        message : `Message`|snowflake
            The message or message ID to pin.
        """
        self.client.api.channels_pins_delete(self.id, to_snowflake(message))

    def get_webhooks(self):
        """
        Returns
        -------
        list(`Webhook`)
            Returns a list of all webhooks for this channel.
        """
        return self.client.api.channels_webhooks_list(self.id)

    def create_webhook(self, *args, **kwargs):
        """
        Creates a webhook for this channel. See `APIClient.channels_webhooks_create`
        for more information.

        Returns
        -------
        `Webhook`
            The created webhook.
        """
        return self.client.api.channels_webhooks_create(self.id, *args, **kwargs)

    def send_message(self, *args, **kwargs):
        """
        Send a message to this channel. See `APIClient.channels_messages_create`
        for more information.

        Returns
        -------
        `disco.types.message.Message`
            The created message.
        """
        return self.client.api.channels_messages_create(self.id, *args, **kwargs)

    def send_typing(self):
        """
        Sends a typing event to this channel. See `APIClient.channels_typing`
        for more information.
        """
        self.client.api.channels_typing(self.id)

    def connect(self, *args, **kwargs):
        """
        Connect to this channel over voice.
        """
        from disco.voice.client import VoiceClient
        assert self.is_voice, 'Channel must support voice to connect'
        vc = VoiceClient(self)
        vc.connect(*args, **kwargs)
        return vc

    def create_overwrite(self, *args, **kwargs):
        """
        Creates a `PermissionOverwrite` for this channel. See
        `PermissionOverwrite.create_for_channel` for more information.
        """
        return PermissionOverwrite.create_for_channel(self, *args, **kwargs)

    def delete_message(self, message):
        """
        Deletes a single message from this channel.

        Args
        ----
        message : snowflake|`Message`
            The message to delete.
        """
        self.client.api.channels_messages_delete(self.id, to_snowflake(message))

    @one_or_many
    def delete_messages(self, messages):
        """
        Deletes a set of messages using the correct API route based on the number
        of messages passed.

        Args
        ----
        messages : list(snowflake|`Message`)
            List of messages (or message ids) to delete. All messages must originate
            from this channel.
        """
        message_ids = list(map(to_snowflake, messages))

        if not message_ids:
            return

        if self.can(self.client.state.me, Permissions.MANAGE_MESSAGES) and len(messages) > 2:
            for chunk in chunks(message_ids, 100):
                self.client.api.channels_messages_delete_bulk(self.id, chunk)
        else:
            for msg in messages:
                self.delete_message(msg)

    def delete(self, **kwargs):
        assert (self.is_dm or self.guild.can(self.client.state.me, Permissions.MANAGE_CHANNELS)), 'Invalid Permissions'
        self.client.api.channels_delete(self.id, **kwargs)

    def close(self):
        """
        Closes a DM channel. This is intended as a safer version of `delete`,
        enforcing that the channel is actually a DM.
        """
        assert self.is_dm, 'Cannot close non-DM channel'
        self.delete()

    def set_topic(self, topic, reason=None):
        """
        Sets the channels topic.
        """
        return self.client.api.channels_modify(self.id, topic=topic, reason=reason)

    def set_name(self, name, reason=None):
        """
        Sets the channels name.
        """
        return self.client.api.channels_modify(self.id, name=name, reason=reason)

    def set_position(self, position, reason=None):
        """
        Sets the channels position.
        """
        return self.client.api.channels_modify(self.id, position=position, reason=reason)

    def set_nsfw(self, value, reason=None):
        """
        Sets whether the channel is NSFW.
        """
        assert (self.type == ChannelType.GUILD_TEXT)
        return self.client.api.channels_modify(self.id, nsfw=value, reason=reason)

    def set_bitrate(self, bitrate, reason=None):
        """
        Sets the channels bitrate.
        """
        assert (self.is_voice)
        return self.client.api.channels_modify(self.id, bitrate=bitrate, reason=reason)

    def set_user_limit(self, user_limit, reason=None):
        """
        Sets the channels user limit.
        """
        assert (self.is_voice)
        return self.client.api.channels_modify(self.id, user_limit=user_limit, reason=reason)

    def set_parent(self, parent, reason=None):
        """
        Sets the channels parent.
        """
        assert (self.is_guild)
        return self.client.api.channels_modify(
            self.id,
            parent_id=to_snowflake(parent) if parent else parent,
            reason=reason)

    def create_text_channel(self, *args, **kwargs):
        """
        Creates a sub-text-channel in this category. See `Guild.create_text_channel`
        for arguments and more information.
        """
        if self.type != ChannelType.GUILD_CATEGORY:
            raise ValueError('Cannot create a sub-channel on a non-category channel')

        kwargs['parent_id'] = self.id
        return self.guild.create_text_channel(
            *args,
            **kwargs
        )

    def create_voice_channel(self, *args, **kwargs):
        """
        Creates a sub-voice-channel in this category. See `Guild.create_voice_channel`
        for arguments and more information.
        """
        if self.type != ChannelType.GUILD_CATEGORY:
            raise ValueError('Cannot create a sub-channel on a non-category channel')

        kwargs['parent_id'] = self.id
        return self.guild.create_voice_channel(
            *args,
            **kwargs
        )


class MessageIterator(object):
    """
    An iterator which supports scanning through the messages for a channel.

    Parameters
    ----------
    client : :class:`disco.client.Client`
        The disco client instance to use when making requests.
    channel : `Channel`
        The channel to iterate within.
    direction : :attr:`MessageIterator.Direction`
        The direction in which this iterator will move.
    bulk : bool
        If true, this iterator will yield messages in list batches, otherwise each
        message will be yield individually.
    before : snowflake
        The message to begin scanning at.
    after : snowflake
        The message to begin scanning at.
    chunk_size : int
        The number of messages to request per API call.
    """
    Direction = Enum('UP', 'DOWN')

    def __init__(self, client, channel, direction=Direction.UP, bulk=False, before=None, after=None, chunk_size=100):
        self.client = client
        self.channel = channel
        self.direction = direction
        self.bulk = bulk
        self.before = before
        self.after = after
        self.chunk_size = chunk_size

        self.last = None
        self._buffer = []

        if before is None and after is None and self.direction == self.Direction.DOWN:
            raise Exception('Must specify either before or after for downward seeking')

    def fill(self):
        """
        Fills the internal buffer up with :class:`disco.types.message.Message` objects from the API.

        Returns a boolean indicating whether items were added to the buffer.
        """
        self._buffer = self.client.api.channels_messages_list(
            self.channel.id,
            before=self.before,
            after=self.after,
            limit=self.chunk_size)

        if not len(self._buffer):
            return False

        self.after = None
        self.before = None

        if self.direction == self.Direction.UP:
            self.before = self._buffer[-1].id

        else:
            self._buffer.reverse()
            self.after = self._buffer[-1].id

        return True

    def next(self):
        return self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        if not len(self._buffer):
            filled = self.fill()
            if not filled:
                raise StopIteration

        if self.bulk:
            res = self._buffer
            self._buffer = []
            return res
        else:
            return self._buffer.pop()
