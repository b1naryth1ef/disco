import six

from holster.enum import Enum

from disco.gateway.packets import OPCode
from disco.api.http import APIException
from disco.util.snowflake import to_snowflake
from disco.util.functional import cached_property
from disco.types.base import (
    SlottedModel, Field, ListField, AutoDictField, snowflake, text, enum, datetime
)
from disco.types.user import User
from disco.types.voice import VoiceState
from disco.types.channel import Channel
from disco.types.message import Emoji
from disco.types.permissions import PermissionValue, Permissions, Permissible


VerificationLevel = Enum(
    NONE=0,
    LOW=1,
    MEDIUM=2,
    HIGH=3,
    EXTREME=4,
)

ExplicitContentFilterLevel = Enum(
    NONE=0,
    WITHOUT_ROLES=1,
    ALL=2
)

DefaultMessageNotificationsLevel = Enum(
    ALL_MESSAGES=0,
    ONLY_MENTIONS=1,
)


class GuildEmoji(Emoji):
    """
    An emoji object.

    Attributes
    ----------
    id : snowflake
        The ID of this emoji.
    name : str
        The name of this emoji.
    require_colons : bool
        Whether this emoji requires colons to use.
    managed : bool
        Whether this emoji is managed by an integration.
    roles : list(snowflake)
        Roles this emoji is attached to.
    """
    id = Field(snowflake)
    guild_id = Field(snowflake)
    name = Field(text)
    require_colons = Field(bool)
    managed = Field(bool)
    roles = ListField(snowflake)

    def __str__(self):
        return u'<:{}:{}>'.format(self.name, self.id)

    def update(self, **kwargs):
        return self.client.api.guilds_emojis_modify(self.guild_id, self.id, **kwargs)

    def delete(self):
        return self.client.api.guilds_emojis_delete(self.guild_id, self.id)

    @property
    def url(self):
        return 'https://discordapp.com/api/emojis/{}.png'.format(self.id)

    @cached_property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


class Role(SlottedModel):
    """
    A role object.

    Attributes
    ----------
    id : snowflake
        The role ID.
    name : string
        The role name.
    hoist : bool
        Whether this role is hoisted (displayed separately in the sidebar).
    managed : bool
        Whether this role is managed by an integration.
    color : int
        The RGB color of this role.
    permissions : :class:`disco.types.permissions.PermissionsValue`
        The permissions this role grants.
    position : int
        The position of this role in the hierarchy.
    """
    id = Field(snowflake)
    guild_id = Field(snowflake)
    name = Field(text)
    hoist = Field(bool)
    managed = Field(bool)
    color = Field(int)
    permissions = Field(PermissionValue)
    position = Field(int)
    mentionable = Field(bool)

    def __str__(self):
        return self.name

    def delete(self):
        self.guild.delete_role(self)

    def save(self):
        self.guild.update_role(self)

    @property
    def mention(self):
        return '<@&{}>'.format(self.id)

    @cached_property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)


class GuildBan(SlottedModel):
    user = Field(User)
    reason = Field(str)


class GuildMember(SlottedModel):
    """
    A GuildMember object.

    Attributes
    ----------
    user : :class:`disco.types.user.User`
        The user object of this member.
    guild_id : snowflake
        The guild this member is part of.
    nick : str
        The nickname of the member.
    mute : bool
        Whether this member is server voice-muted.
    deaf : bool
        Whether this member is server voice-deafened.
    joined_at : datetime
        When this user joined the guild.
    roles : list(snowflake)
        Roles this member is part of.
    """
    user = Field(User)
    guild_id = Field(snowflake)
    nick = Field(text)
    mute = Field(bool)
    deaf = Field(bool)
    joined_at = Field(datetime)
    roles = ListField(snowflake)

    def __str__(self):
        return self.user.__str__()

    @property
    def name(self):
        """
        The nickname of this user if set, otherwise their username
        """
        return self.nick or self.user.username

    def get_voice_state(self):
        """
        Returns
        -------
        Optional[:class:`disco.types.voice.VoiceState`]
            Returns the voice state for the member if they are currently connected
            to the guild's voice server.
        """
        return self.guild.get_voice_state(self)

    def kick(self):
        """
        Kicks the member from the guild.
        """
        self.client.api.guilds_members_kick(self.guild.id, self.user.id)

    def ban(self, delete_message_days=0):
        """
        Bans the member from the guild.

        Args
        ----
        delete_message_days : int
            The number of days to retroactively delete messages for.
        """
        self.guild.create_ban(self, delete_message_days)

    def unban(self):
        """
        Unbans the member from the guild.
        """
        self.guild.delete_ban(self)

    def set_nickname(self, nickname=None):
        """
        Sets the member's nickname (or clears it if None).

        Args
        ----
        nickname : Optional[str]
            The nickname (or none to reset) to set.
        """
        if self.client.state.me.id == self.user.id:
            self.client.api.guilds_members_me_nick(self.guild.id, nick=nickname or '')
        else:
            self.client.api.guilds_members_modify(self.guild.id, self.user.id, nick=nickname or '')

    def modify(self, **kwargs):
        self.client.api.guilds_members_modify(self.guild.id, self.user.id, **kwargs)

    def add_role(self, role):
        self.client.api.guilds_members_roles_add(self.guild.id, self.user.id, to_snowflake(role))

    def remove_role(self, role):
        self.client.api.guilds_members_roles_remove(self.guild.id, self.user.id, to_snowflake(role))

    @cached_property
    def owner(self):
        return self.guild.owner_id == self.id

    @cached_property
    def mention(self):
        if self.nick:
            return '<@!{}>'.format(self.id)
        return self.user.mention

    @property
    def id(self):
        """
        Alias to the guild members user id.
        """
        return self.user.id

    @cached_property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)

    @cached_property
    def permissions(self):
        return self.guild.get_permissions(self)


class Guild(SlottedModel, Permissible):
    """
    A guild object.

    Attributes
    ----------
    id : snowflake
        The id of this guild.
    owner_id : snowflake
        The id of the owner.
    afk_channel_id : snowflake
        The id of the afk channel.
    embed_channel_id : snowflake
        The id of the embed channel.
    name : str
        Guild's name.
    icon : str
        Guild's icon hash
    splash : str
        Guild's splash image hash
    region : str
        Voice region.
    afk_timeout : int
        Delay after which users are automatically moved to the afk channel.
    embed_enabled : bool
        Whether the guild's embed is enabled.
    verification_level : int
        The verification level used by the guild.
    mfa_level : int
        The MFA level used by the guild.
    features : list(str)
        Extra features enabled for this guild.
    members : dict(snowflake, :class:`GuildMember`)
        All of the guild's members.
    channels : dict(snowflake, :class:`disco.types.channel.Channel`)
        All of the guild's channels.
    roles : dict(snowflake, :class:`Role`)
        All of the guild's roles.
    emojis : dict(snowflake, :class:`GuildEmoji`)
        All of the guild's emojis.
    voice_states : dict(str, :class:`disco.types.voice.VoiceState`)
        All of the guild's voice states.
    """
    id = Field(snowflake)
    owner_id = Field(snowflake)
    afk_channel_id = Field(snowflake)
    embed_channel_id = Field(snowflake)
    name = Field(text)
    icon = Field(text)
    splash = Field(text)
    region = Field(text)
    afk_timeout = Field(int)
    embed_enabled = Field(bool)
    verification_level = Field(enum(VerificationLevel))
    explicit_content_filter = Field(enum(ExplicitContentFilterLevel))
    default_message_notifications = Field(enum(DefaultMessageNotificationsLevel))
    mfa_level = Field(int)
    features = ListField(str)
    members = AutoDictField(GuildMember, 'id')
    channels = AutoDictField(Channel, 'id')
    roles = AutoDictField(Role, 'id')
    emojis = AutoDictField(GuildEmoji, 'id')
    voice_states = AutoDictField(VoiceState, 'session_id')
    member_count = Field(int)

    synced = Field(bool, default=False)

    def __init__(self, *args, **kwargs):
        super(Guild, self).__init__(*args, **kwargs)

        self.attach(six.itervalues(self.channels), {'guild_id': self.id})
        self.attach(six.itervalues(self.members), {'guild_id': self.id})
        self.attach(six.itervalues(self.roles), {'guild_id': self.id})
        self.attach(six.itervalues(self.emojis), {'guild_id': self.id})
        self.attach(six.itervalues(self.voice_states), {'guild_id': self.id})

    @cached_property
    def owner(self):
        return self.members.get(self.owner_id)

    def get_permissions(self, member):
        """
        Get the permissions a user has in this guild.

        Returns
        -------
        :class:`disco.types.permissions.PermissionValue`
            Computed permission value for the user.
        """
        if not isinstance(member, GuildMember):
            member = self.get_member(member)

        # Owner has all permissions
        if self.owner_id == member.id:
            return PermissionValue(Permissions.ADMINISTRATOR)

        value = PermissionValue(self.roles.get(self.id).permissions)

        # Iterate over all roles the user has (plus the @everyone role)
        for role in map(self.roles.get, member.roles + [self.id]):
            value += role.permissions

        return value

    def get_voice_state(self, user):
        """
        Attempt to get a voice state for a given user (who should be a member of
        this guild).

        Returns
        -------
        :class:`disco.types.voice.VoiceState`
            The voice state for the user in this guild.
        """
        user = to_snowflake(user)

        for state in six.itervalues(self.voice_states):
            if state.user_id == user:
                return state

    def get_member(self, user):
        """
        Attempt to get a member from a given user.

        Returns
        -------
        :class:`GuildMember`
            The guild member object for the given user.
        """
        user = to_snowflake(user)

        if user not in self.members:
            try:
                self.members[user] = self.client.api.guilds_members_get(self.id, user)
            except APIException:
                return

        return self.members.get(user)

    def create_role(self):
        """
        Create a new role.

        Returns
        -------
        :class:`Role`
            The newly created role.
        """
        return self.client.api.guilds_roles_create(self.id)

    def delete_role(self, role):
        """
        Delete a role.
        """
        self.client.api.guilds_roles_delete(self.id, to_snowflake(role))

    def update_role(self, role):
        return self.client.api.guilds_roles_modify(self.id, role.id, **{
            'name': role.name,
            'permissions': role.permissions.value,
            'position': role.position,
            'color': role.color,
            'hoist': role.hoist,
            'mentionable': role.mentionable,
        })

    def sync(self):
        if self.synced:
            return

        self.synced = True
        self.client.gw.send(OPCode.REQUEST_GUILD_MEMBERS, {
            'guild_id': self.id,
            'query': '',
            'limit': 0,
        })

    def get_bans(self):
        return self.client.api.guilds_bans_list(self.id)

    def delete_ban(self, user):
        self.client.api.guilds_bans_delete(self.id, to_snowflake(user))

    def create_ban(self, user, delete_message_days=0):
        self.client.api.guilds_bans_create(self.id, to_snowflake(user), delete_message_days)

    def create_channel(self, *args, **kwargs):
        return self.client.api.guilds_channels_create(self.id, *args, **kwargs)

    def leave(self):
        return self.client.api.users_me_guilds_delete(self.id)

    def get_invites(self):
        return self.client.api.guilds_invites_list(self.id)

    def get_emojis(self):
        return self.client.api.guilds_emojis_list(self.id)

    def get_icon_url(self, fmt='webp', size=1024):
        if not self.icon:
            return ''

        return 'https://cdn.discordapp.com/icons/{}/{}.{}?size={}'.format(self.id, self.icon, fmt, size)

    def get_splash_url(self, fmt='webp', size=1024):
        if not self.splash:
            return ''

        return 'https://cdn.discordapp.com/splashes/{}/{}.{}?size={}'.format(self.id, self.splash, fmt, size)

    @property
    def icon_url(self):
        return self.get_icon_url()

    @property
    def splash_url(self):
        return self.get_splash_url()
