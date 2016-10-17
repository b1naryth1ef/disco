from __future__ import print_function

import inflection
import six

from disco.types.user import User, Presence
from disco.types.channel import Channel
from disco.types.message import Message
from disco.types.voice import VoiceState
from disco.types.guild import Guild, GuildMember, Role

from disco.types.base import Model, ModelMeta, Field, snowflake, listof, lazy_datetime

# Mapping of discords event name to our event classes
EVENTS_MAP = {}


class GatewayEventMeta(ModelMeta):
    def __new__(cls, name, parents, dct):
        obj = super(GatewayEventMeta, cls).__new__(cls, name, parents, dct)

        if name != 'GatewayEvent':
            EVENTS_MAP[inflection.underscore(name).upper()] = obj

        return obj


class GatewayEvent(six.with_metaclass(GatewayEventMeta, Model)):
    """
    The GatewayEvent class wraps various functionality for events passed to us
    over the gateway websocket, and serves as a simple proxy to inner values for
    some wrapped event-types (e.g. MessageCreate only contains a message, so we
    proxy all attributes to the inner message object).
    """

    @staticmethod
    def from_dispatch(client, data):
        """
        Create a new GatewayEvent instance based on event data.
        """
        cls = EVENTS_MAP.get(data['t'])
        if not cls:
            raise Exception('Could not find cls for {} ({})'.format(data['t'], data))

        return cls.create(data['d'], client)

    @classmethod
    def create(cls, obj, client):
        """
        Create this GatewayEvent class from data and the client.
        """
        cls.raw_data = obj

        # If this event is wrapping a model, pull its fields
        if hasattr(cls, '_wraps_model'):
            alias, model = cls._wraps_model

            data = {
                k: obj.pop(k) for k in six.iterkeys(model._fields) if k in obj
            }

            obj[alias] = data

        return cls(obj, client)

    def __getattr__(self, name):
        if hasattr(self, '_wraps_model'):
            modname, _ = self._wraps_model
            if hasattr(self, modname) and hasattr(getattr(self, modname), name):
                return getattr(getattr(self, modname), name)
        raise AttributeError(name)


def debug(func=None):
    def deco(cls):
        old_init = cls.__init__

        def new_init(self, obj, *args, **kwargs):
            if func:
                print(func(obj))
            else:
                print(obj)

            old_init(self, obj, *args, **kwargs)

        cls.__init__ = new_init
        return cls
    return deco


def wraps_model(model, alias=None):
    alias = alias or model.__name__.lower()

    def deco(cls):
        cls._fields[alias] = Field(model)
        cls._fields[alias].set_name(alias)
        cls._wraps_model = (alias, model)
        return cls
    return deco


class Ready(GatewayEvent):
    """
    Sent after the initial gateway handshake is complete. Contains data required
    for bootstrapping the client's states.
    """
    version = Field(int, alias='v')
    session_id = Field(str)
    user = Field(User)
    guilds = Field(listof(Guild))
    private_channels = Field(listof(Channel))


class Resumed(GatewayEvent):
    """
    Sent after a resume completes.
    """
    pass


@wraps_model(Guild)
class GuildCreate(GatewayEvent):
    """
    Sent when a guild is created, or becomes available.
    """
    unavailable = Field(bool)


@wraps_model(Guild)
class GuildUpdate(GatewayEvent):
    """
    Sent when a guild is updated.
    """
    pass


class GuildDelete(GatewayEvent):
    """
    Sent when a guild is deleted, or becomes unavailable.
    """
    id = Field(snowflake)
    unavailable = Field(bool)


@wraps_model(Channel)
class ChannelCreate(GatewayEvent):
    """
    Sent when a channel is created.
    """


@wraps_model(Channel)
class ChannelUpdate(ChannelCreate):
    """
    Sent when a channel is updated.
    """
    pass


@wraps_model(Channel)
class ChannelDelete(ChannelCreate):
    """
    Sent when a channel is deleted.
    """
    pass


class ChannelPinsUpdate(GatewayEvent):
    """
    Sent when a channel's pins are updated.
    """
    channel_id = Field(snowflake)
    last_pin_timestamp = Field(lazy_datetime)


@wraps_model(User)
class GuildBanAdd(GatewayEvent):
    """
    Sent when a user is banned from a guild.
    """
    pass


@wraps_model(User)
class GuildBanRemove(GuildBanAdd):
    """
    Sent when a user is unbanned from a guild.
    """
    pass


class GuildEmojisUpdate(GatewayEvent):
    """
    Sent when a guild's emojis are updated.
    """
    pass


class GuildIntegrationsUpdate(GatewayEvent):
    """
    Sent when a guild's integrations are updated.
    """
    pass


class GuildMembersChunk(GatewayEvent):
    """
    Sent in response to a member's chunk request.
    """
    guild_id = Field(snowflake)
    members = Field(listof(GuildMember))


@wraps_model(GuildMember, alias='member')
class GuildMemberAdd(GatewayEvent):
    """
    Sent when a user joins a guild.
    """
    pass


class GuildMemberRemove(GatewayEvent):
    """
    Sent when a user leaves a guild (via leaving, kicking, or banning).
    """
    guild_id = Field(snowflake)
    user = Field(User)


@wraps_model(GuildMember, alias='member')
class GuildMemberUpdate(GatewayEvent):
    """
    Sent when a guilds member is updated.
    """
    pass


class GuildRoleCreate(GatewayEvent):
    """
    Sent when a role is created.
    """
    guild_id = Field(snowflake)
    role = Field(Role)


class GuildRoleUpdate(GuildRoleCreate):
    """
    Sent when a role is updated.
    """
    pass


class GuildRoleDelete(GatewayEvent):
    """
    Sent when a role is deleted.
    """
    guild_id = Field(snowflake)
    role_id = Field(snowflake)


@wraps_model(Message)
class MessageCreate(GatewayEvent):
    """
    Sent when a message is created.
    """


@wraps_model(Message)
class MessageUpdate(MessageCreate):
    """
    Sent when a message is updated/edited.
    """
    pass


class MessageDelete(GatewayEvent):
    """
    Sent when a message is deleted.
    """
    id = Field(snowflake)
    channel_id = Field(snowflake)


class MessageDeleteBulk(GatewayEvent):
    """
    Sent when multiple messages are deleted from a channel.
    """
    channel_id = Field(snowflake)
    ids = Field(listof(snowflake))


@wraps_model(Presence)
class PresenceUpdate(GatewayEvent):
    """
    Sent when a user's presence is updated.
    """
    guild_id = Field(snowflake)
    roles = Field(listof(snowflake))


class TypingStart(GatewayEvent):
    """
    Sent when a user begins typing in a channel.
    """
    channel_id = Field(snowflake)
    user_id = Field(snowflake)
    timestamp = Field(snowflake)


@wraps_model(VoiceState, alias='state')
class VoiceStateUpdate(GatewayEvent):
    """
    Sent when a users voice state changes.
    """
    pass


class VoiceServerUpdate(GatewayEvent):
    """
    Sent when a voice server is updated.
    """
    token = Field(str)
    endpoint = Field(str)
    guild_id = Field(snowflake)


class WebhooksUpdate(GatewayEvent):
    """
    Sent when a channels webhooks are updated.
    """
    channel_id = Field(snowflake)
    guild_id = Field(snowflake)
