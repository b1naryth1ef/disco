import skema

from holster.enum import Enum

from disco.util.cache import cached_property
from disco.util.types import ListToDictType
from disco.types.base import BaseType
from disco.types.user import User
from disco.types.permissions import *
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


class PermissionOverwrite(BaseType):
    id = skema.SnowflakeType()
    type = skema.StringType(choices=PermissionOverwriteType.ALL_VALUES)

    allow = PermissionType()
    deny = PermissionType()


class Channel(BaseType):
    id = skema.SnowflakeType()
    guild_id = skema.SnowflakeType(required=False)

    name = skema.StringType()
    topic = skema.StringType()
    _last_message_id = skema.SnowflakeType(stored_name='last_message_id')
    position = skema.IntType()
    bitrate = skema.IntType(required=False)

    recipient = skema.ModelType(User, required=False)
    type = skema.IntType(choices=ChannelType.ALL_VALUES)

    overwrites = ListToDictType('id', skema.ModelType(PermissionOverwrite), stored_name='permission_overwrites')

    @property
    def is_guild(self):
        return self.type in (ChannelType.GUILD_TEXT, ChannelType.GUILD_VOICE)

    @property
    def is_dm(self):
        return self.type in (ChannelType.DM, ChannelType.GROUP_DM)

    @property
    def is_voice(self):
        return self.type in (ChannelType.GUILD_VOICE, ChannelType.GROUP_DM)

    @property
    def last_message_id(self):
        if self.id not in self.client.state.messages:
            return self._last_message_id
        return self.client.state.messages[self.id][-1].id

    @property
    def messages(self):
        return self.messages_iter()

    def messages_iter(self, **kwargs):
        return MessageIterator(self.client, self.id, before=self.last_message_id, **kwargs)

    @cached_property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)

    def get_invites(self):
        return self.client.api.channels_invites_list(self.id)

    def get_pins(self):
        return self.client.api.channels_pins_list(self.id)

    def send_message(self, content, nonce=None, tts=False):
        return self.client.api.channels_messages_create(self.id, content, nonce, tts)

    def connect(self, *args, **kwargs):
        vc = VoiceClient(self)
        vc.connect(*args, **kwargs)
        return vc


class MessageIterator(object):
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

        if len(filter(bool, (before, after))) > 1:
            raise Exception('Must specify at most one of before or after')

        if not any((before, after)) and self.direction == self.Direction.DOWN:
            raise Exception('Must specify either before or after for downward seeking')

    def fill(self):
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

    def __iter__(self):
        return self

    def next(self):
        if not len(self._buffer):
            self.fill()

        if self.bulk:
            res = self._buffer
            self._buffer = []
            return res
        else:
            return self._buffer.pop()
