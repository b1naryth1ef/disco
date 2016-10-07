from holster.enum import Enum

from disco.types.base import Model, snowflake, enum, listof, dictof, alias, text
from disco.types.permissions import PermissionValue

from disco.util.functional import cached_property
from disco.types.user import User
from disco.types.permissions import Permissions, Permissible
from disco.voice.client import VoiceClient


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


class PermissionOverwrite(Model):
    """
    A PermissionOverwrite for a :class:`Channel`


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

    id = snowflake
    type = enum(PermissionOverwriteType)
    allow = PermissionValue
    deny = PermissionValue


class Channel(Model, Permissible):
    """
    Represents a Discord Channel

    Attributes
    ----------
    id : snowflake
        The channel ID.
    guild_id : Optional[snowflake]
        The guild id this channel is part of.
    name : str
        The channels name.
    topic : str
        The channels topic.
    position : int
        The channels position.
    bitrate : int
        The channels bitrate.
    recipients: list(:class:`disco.types.user.User`)
        Members of this channel (if this is a DM channel).
    type : :const:`ChannelType`
        The type of this channel.
    overwrites : dict(snowflake, :class:`disco.types.channel.PermissionOverwrite`)
        Channel permissions overwrites.
    """
    id = snowflake
    guild_id = snowflake
    name = text
    topic = text
    _last_message_id = alias(snowflake, 'last_message_id')
    position = int
    bitrate = int
    recipients = listof(User)
    type = enum(ChannelType)
    overwrites = alias(dictof(PermissionOverwrite, key='id'), 'permission_overwrites')

    def get_permissions(self, user):
        """
        Get the permissions a user has in the channel

        Returns
        -------
        :class:`disco.types.permissions.PermissionValue`
            Computed permission value for the user.
        """
        if not self.guild_id:
            return Permissions.ADMINISTRATOR

        member = self.guild.members.get(user.id)
        base = self.guild.get_permissions(user)

        for ow in self.overwrites.values():
            if ow.id != user.id and ow.id not in member.roles:
                continue

            base -= ow.deny
            base += ow.allow

        return base

    @property
    def is_guild(self):
        """
        Whether this channel belongs to a guild
        """
        return self.type in (ChannelType.GUILD_TEXT, ChannelType.GUILD_VOICE)

    @property
    def is_dm(self):
        """
        Whether this channel is a DM (does not belong to a guild)
        """
        return self.type in (ChannelType.DM, ChannelType.GROUP_DM)

    @property
    def is_voice(self):
        """
        Whether this channel supports voice
        """
        return self.type in (ChannelType.GUILD_VOICE, ChannelType.GROUP_DM)

    @property
    def last_message_id(self):
        """
        Returns the ID of the last message sent in this channel
        """
        if self.id not in self.client.state.messages:
            return self._last_message_id
        return self.client.state.messages[self.id][-1].id

    @property
    def messages(self):
        """
        a default :class:`MessageIterator` for the channel
        """
        return self.messages_iter()

    def messages_iter(self, **kwargs):
        """
        Creates a new :class:`MessageIterator` for the channel with the given
        keyword arguments
        """
        return MessageIterator(self.client, self.id, before=self.last_message_id, **kwargs)

    @cached_property
    def guild(self):
        """
        Guild this channel belongs to (if relevant)
        """
        return self.client.state.guilds.get(self.guild_id)

    def get_invites(self):
        """
        Returns
        -------
        list(:class:`disco.types.invite.Invite`)
            All invites for this channel.
        """
        return self.client.api.channels_invites_list(self.id)

    def get_pins(self):
        """
        Returns
        -------
        list(:class:`disco.types.message.Message`)
            All pinned messages for this channel.
        """
        return self.client.api.channels_pins_list(self.id)

    def send_message(self, content, nonce=None, tts=False):
        """
        Send a message in this channel

        Parameters
        ----------
        content : str
            The message contents to send.
        nonce : Optional[snowflake]
            The nonce to attach to the message.
        tts : Optional[bool]
            Whether this is a TTS message.

        Returns
        -------
        :class:`disco.types.message.Message`
            The created message.
        """
        return self.client.api.channels_messages_create(self.id, content, nonce, tts)

    def connect(self, *args, **kwargs):
        """
        Connect to this channel over voice
        """
        assert self.is_voice, 'Channel must support voice to connect'
        vc = VoiceClient(self)
        vc.connect(*args, **kwargs)
        return vc


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

        if not before and not after:
            raise Exception('Must specify at most one of before or after')

        if not any((before, after)) and self.direction == self.Direction.DOWN:
            raise Exception('Must specify either before or after for downward seeking')

    def fill(self):
        """
        Fills the internal buffer up with :class:`disco.types.message.Message` objects from the API
        """
        self._buffer = self.client.api.channels_messages_list(
                self.channel,
                before=self.before,
                after=self.after,
                limit=self.chunk_size)

        if not len(self._buffer):
            raise StopIteration

        self.after = None
        self.before = None

        if self.direction == self.Direction.UP:
            self.before = self._buffer[-1].id
        else:
            self._buffer.reverse()
            self.after == self._buffer[-1].id

    def next(self):
        return self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        if not len(self._buffer):
            self.fill()

        if self.bulk:
            res = self._buffer
            self._buffer = []
            return res
        else:
            return self._buffer.pop()
