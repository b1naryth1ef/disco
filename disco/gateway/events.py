from __future__ import print_function

import six

from disco.types.user import User, Presence
from disco.types.channel import Channel, PermissionOverwrite
from disco.types.message import Message, MessageReactionEmoji
from disco.types.voice import VoiceState
from disco.types.guild import Guild, GuildMember, Role, GuildEmoji
from disco.types.base import Model, ModelMeta, Field, ListField, AutoDictField, snowflake, datetime
from disco.util.string import underscore

# Mapping of discords event name to our event classes
EVENTS_MAP = {}


class GatewayEventMeta(ModelMeta):
    def __new__(mcs, name, parents, dct):
        obj = super(GatewayEventMeta, mcs).__new__(mcs, name, parents, dct)

        if name != 'GatewayEvent':
            EVENTS_MAP[underscore(name).upper()] = obj

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

        obj = cls(obj, client)

        if hasattr(cls, '_attach'):
            field, to = cls._attach
            setattr(getattr(obj, to[0]), to[1], getattr(obj, field))

        return obj

    def __getattr__(self, name):
        try:
            _proxy = object.__getattribute__(self, '_proxy')
        except AttributeError:
            return object.__getattribute__(self, name)

        return getattr(getattr(self, _proxy), name)


def debug(func=None, match=None):
    def deco(cls):
        old_init = cls.__init__

        def new_init(self, obj, *args, **kwargs):
            if not match or match(obj):
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
        cls._fields[alias].name = alias
        cls._wraps_model = (alias, model)
        cls._proxy = alias
        return cls
    return deco


def proxy(field):
    def deco(cls):
        cls._proxy = field
        return cls
    return deco


def attach(field, to=None):
    def deco(cls):
        cls._attach = (field, to)
        return cls
    return deco


class Ready(GatewayEvent):
    """
    Sent after the initial gateway handshake is complete. Contains data required
    for bootstrapping the client's states.

    Attributes
    -----
    version : int
        The gateway version.
    session_id : str
        The session ID.
    user : :class:`disco.types.user.User`
        The user object for the authed account.
    guilds : list[:class:`disco.types.guild.Guild`
        All guilds this account is a member of. These are shallow guild objects.
    private_channels list[:class:`disco.types.channel.Channel`]
        All private channels (DMs) open for this account.
    """
    version = Field(int, alias='v')
    session_id = Field(str)
    user = Field(User)
    guilds = ListField(Guild)
    private_channels = ListField(Channel)
    trace = ListField(str, alias='_trace')


class Resumed(GatewayEvent):
    """
    Sent after a resume completes.
    """
    trace = ListField(str, alias='_trace')


@wraps_model(Guild)
class GuildCreate(GatewayEvent):
    """
    Sent when a guild is joined, or becomes available.

    Attributes
    -----
    guild : :class:`disco.types.guild.Guild`
        The guild being created (e.g. joined)
    unavailable : bool
        If false, this guild is coming online from a previously unavailable state,
        and if None, this is a normal guild join event.
    """
    unavailable = Field(bool)
    presences = ListField(Presence)

    @property
    def created(self):
        """
        Shortcut property which is true when we actually joined the guild.
        """
        return self.unavailable is None


@wraps_model(Guild)
class GuildUpdate(GatewayEvent):
    """
    Sent when a guild is updated.

    Attributes
    -----
    guild : :class:`disco.types.guild.Guild`
        The updated guild object.
    """


class GuildDelete(GatewayEvent):
    """
    Sent when a guild is deleted, left, or becomes unavailable.

    Attributes
    -----
    id : snowflake
        The ID of the guild being deleted.
    unavailable : bool
        If true, this guild is becoming unavailable, if None this is a normal
        guild leave event.
    """
    id = Field(snowflake)
    unavailable = Field(bool)

    @property
    def deleted(self):
        """
        Shortcut property which is true when we actually have left the guild.
        """
        return self.unavailable is None


@wraps_model(Channel)
class ChannelCreate(GatewayEvent):
    """
    Sent when a channel is created.

    Attributes
    -----
    channel : :class:`disco.types.channel.Channel`
        The channel which was created.
    """


@wraps_model(Channel)
class ChannelUpdate(ChannelCreate):
    """
    Sent when a channel is updated.

    Attributes
    -----
    channel : :class:`disco.types.channel.Channel`
        The channel which was updated.
    """
    overwrites = AutoDictField(PermissionOverwrite, 'id', alias='permission_overwrites')


@wraps_model(Channel)
class ChannelDelete(ChannelCreate):
    """
    Sent when a channel is deleted.

    Attributes
    -----
    channel : :class:`disco.types.channel.Channel`
        The channel being deleted.
    """


class ChannelPinsUpdate(GatewayEvent):
    """
    Sent when a channel's pins are updated.

    Attributes
    -----
    channel_id : snowflake
        ID of the channel where pins where updated.
    last_pin_timestap : datetime
        The time the last message was pinned.
    """
    channel_id = Field(snowflake)
    last_pin_timestamp = Field(datetime)


@proxy(User)
class GuildBanAdd(GatewayEvent):
    """
    Sent when a user is banned from a guild.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild the user is being banned from.
    user : :class:`disco.types.user.User`
        The user being banned from the guild.
    """
    guild_id = Field(snowflake)
    user = Field(User)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


@proxy(User)
class GuildBanRemove(GuildBanAdd):
    """
    Sent when a user is unbanned from a guild.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild the user is being unbanned from.
    user : :class:`disco.types.user.User`
        The user being unbanned from the guild.
    """

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


class GuildEmojisUpdate(GatewayEvent):
    """
    Sent when a guild's emojis are updated.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild the emojis are being updated in.
    emojis : list[:class:`disco.types.guild.Emoji`]
        The new set of emojis for the guild
    """
    guild_id = Field(snowflake)
    emojis = ListField(GuildEmoji)


class GuildIntegrationsUpdate(GatewayEvent):
    """
    Sent when a guild's integrations are updated.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild integrations where updated in.
    """
    guild_id = Field(snowflake)


class GuildMembersChunk(GatewayEvent):
    """
    Sent in response to a member's chunk request.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild this member chunk is for.
    members : list[:class:`disco.types.guild.GuildMember`]
        The chunk of members.
    """
    guild_id = Field(snowflake)
    members = ListField(GuildMember)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


@wraps_model(GuildMember, alias='member')
class GuildMemberAdd(GatewayEvent):
    """
    Sent when a user joins a guild.

    Attributes
    -----
    member : :class:`disco.types.guild.GuildMember`
        The member that has joined the guild.
    """


@proxy('user')
class GuildMemberRemove(GatewayEvent):
    """
    Sent when a user leaves a guild (via leaving, kicking, or banning).

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild the member left from.
    user : :class:`disco.types.user.User`
        The user who was removed from the guild.
    """
    user = Field(User)
    guild_id = Field(snowflake)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


@wraps_model(GuildMember, alias='member')
class GuildMemberUpdate(GatewayEvent):
    """
    Sent when a guilds member is updated.

    Attributes
    -----
    member : :class:`disco.types.guild.GuildMember`
        The member being updated
    """


@proxy('role')
@attach('guild_id', to=('role', 'guild_id'))
class GuildRoleCreate(GatewayEvent):
    """
    Sent when a role is created.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild where the role was created.
    role : :class:`disco.types.guild.Role`
        The role that was created.
    """
    role = Field(Role)
    guild_id = Field(snowflake)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


class GuildRoleUpdate(GuildRoleCreate):
    """
    Sent when a role is updated.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild where the role was created.
    role : :class:`disco.types.guild.Role`
        The role that was created.
    """

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


class GuildRoleDelete(GatewayEvent):
    """
    Sent when a role is deleted.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild where the role is being deleted.
    role_id : snowflake
        The id of the role being deleted.
    """
    guild_id = Field(snowflake)
    role_id = Field(snowflake)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


@wraps_model(Message)
class MessageCreate(GatewayEvent):
    """
    Sent when a message is created.

    Attributes
    -----
    message : :class:`disco.types.message.Message`
        The message being created.
    guild_id : snowflake
        The ID of the guild this message comes from.
    """
    guild_id = Field(snowflake)


@wraps_model(Message)
class MessageUpdate(MessageCreate):
    """
    Sent when a message is updated/edited.

    Attributes
    -----
    message : :class:`disco.types.message.Message`
        The message being updated.
    guild_id : snowflake
        The ID of the guild this message exists in.
    """
    guild_id = Field(snowflake)


class MessageDelete(GatewayEvent):
    """
    Sent when a message is deleted.

    Attributes
    -----
    id : snowflake
        The ID of message being deleted.
    channel_id : snowflake
        The ID of the channel the message was deleted in.
    guild_id : snowflake
        The ID of the guild this message existed in.
    """
    id = Field(snowflake)
    channel_id = Field(snowflake)
    guild_id = Field(snowflake)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def guild(self):
        return self.channel.guild


class MessageDeleteBulk(GatewayEvent):
    """
    Sent when multiple messages are deleted from a channel.

    Attributes
    -----
    guild_id : snowflake
        The guild the messages are being deleted in.
    channel_id : snowflake
        The channel the messages are being deleted in.
    ids : list[snowflake]
        List of messages being deleted in the channel.
    """
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    ids = ListField(snowflake)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def guild(self):
        return self.channel.guild


@wraps_model(Presence)
class PresenceUpdate(GatewayEvent):
    """
    Sent when a user's presence is updated.

    Attributes
    -----
    presence : :class:`disco.types.user.Presence`
        The updated presence object.
    guild_id : snowflake
        The guild this presence update is for.
    roles : list[snowflake]
        List of roles the user from the presence is part of.
    """
    guild_id = Field(snowflake)
    roles = ListField(snowflake)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


class TypingStart(GatewayEvent):
    """
    Sent when a user begins typing in a channel.

    Attributes
    -----
    guild_id : snowflake
        The ID of the guild where the user is typing.
    channel_id : snowflake
        The ID of the channel where the user is typing.
    user_id : snowflake
        The ID of the user who is typing.
    timestamp : datetime
        When the user started typing.
    """
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    user_id = Field(snowflake)
    timestamp = Field(datetime)


@wraps_model(VoiceState, alias='state')
class VoiceStateUpdate(GatewayEvent):
    """
    Sent when a users voice state changes.

    Attributes
    -----
    state : :class:`disco.models.voice.VoiceState`
        The voice state which was updated.
    """


class VoiceServerUpdate(GatewayEvent):
    """
    Sent when a voice server is updated.

    Attributes
    -----
    token : str
        The token for the voice server.
    endpoint : str
        The endpoint for the voice server.
    guild_id : snowflake
        The guild ID this voice server update is for.
    """
    token = Field(str)
    endpoint = Field(str)
    guild_id = Field(snowflake)


class WebhooksUpdate(GatewayEvent):
    """
    Sent when a channels webhooks are updated.

    Attributes
    -----
    channel_id : snowflake
        The channel ID this webhooks update is for.
    guild_id : snowflake
        The guild ID this webhooks update is for.
    """
    channel_id = Field(snowflake)
    guild_id = Field(snowflake)


class MessageReactionAdd(GatewayEvent):
    """
    Sent when a reaction is added to a message.

    Attributes
    ----------
    guild_id : snowflake
        The guild ID the message is in.
    channel_id : snowflake
        The channel ID the message is in.
    message_id : snowflake
        The ID of the message for which the reaction was added too.
    user_id : snowflake
        The ID of the user who added the reaction.
    emoji : :class:`disco.types.message.MessageReactionEmoji`
        The emoji which was added.
    """
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    message_id = Field(snowflake)
    user_id = Field(snowflake)
    emoji = Field(MessageReactionEmoji)

    def delete(self):
        self.client.api.channels_messages_reactions_delete(
            self.channel_id,
            self.message_id,
            self.emoji.to_string() if self.emoji.id else self.emoji.name,
            self.user_id,
        )

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def guild(self):
        return self.channel.guild


class MessageReactionRemove(GatewayEvent):
    """
    Sent when a reaction is removed from a message.

    Attributes
    ----------
    guild_id : snowflake
        The guild ID the message is in.
    channel_id : snowflake
        The channel ID the message is in.
    message_id : snowflake
        The ID of the message for which the reaction was removed from.
    user_id : snowflake
        The ID of the user who originally added the reaction.
    emoji : :class:`disco.types.message.MessageReactionEmoji`
        The emoji which was removed.
    """
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    message_id = Field(snowflake)
    user_id = Field(snowflake)
    emoji = Field(MessageReactionEmoji)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def guild(self):
        return self.channel.guild


class MessageReactionRemoveAll(GatewayEvent):
    """
    Sent when all reactions are removed from a message.

    Attributes
    ----------
    guild_id : snowflake
        The guild ID the message is in.
    channel_id : snowflake
        The channel ID the message is in.
    message_id : snowflake
        The ID of the message for which the reactions where removed from.
    """
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    message_id = Field(snowflake)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def guild(self):
        return self.channel.guild
