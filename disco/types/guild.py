from holster.enum import Enum

from disco.api.http import APIException
from disco.util import to_snowflake
from disco.types.base import Model, snowflake, listof, dictof, datetime, text, binary, enum
from disco.types.user import User
from disco.types.voice import VoiceState
from disco.types.permissions import PermissionValue, Permissions, Permissible
from disco.types.channel import Channel


VerificationLevel = Enum(
    NONE=0,
    LOW=1,
    MEDIUM=2,
    HIGH=3,
    EXTREME=4,
)


class Emoji(Model):
    """
    An emoji object

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
    id = snowflake
    name = text
    require_colons = bool
    managed = bool
    roles = listof(snowflake)


class Role(Model):
    """
    A role object

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
    id = snowflake
    name = text
    hoist = bool
    managed = bool
    color = int
    permissions = PermissionValue
    position = int


class GuildMember(Model):
    """
    A GuildMember object

    Attributes
    ----------
    user : :class:`disco.types.user.User`
        The user object of this member.
    guild_id : snowflake
        The guild this member is part of.
    mute : bool
        Whether this member is server voice-muted.
    deaf : bool
        Whether this member is server voice-deafend.
    joined_at : datetime
        When this user joined the guild.
    roles : list(snowflake)
        Roles this member is part of.
    """
    user = User
    guild_id = snowflake
    mute = bool
    deaf = bool
    joined_at = datetime
    roles = listof(snowflake)

    def get_voice_state(self):
        """
        Returns
        -------
        Optional[:class:`disco.types.voice.VoiceState`]
            Returns the voice state for the member if they are currently connected
            to the guilds voice server.
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
        self.client.api.guilds_bans_create(self.guild.id, self.user.id, delete_message_days)

    @property
    def id(self):
        """
        Alias to the guild members user id
        """
        return self.user.id


class Guild(Model, Permissible):
    """
    A guild object

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
        Guilds name.
    icon : str
        Guilds icon (as PNG binary data).
    splash : str
        Guilds splash image (as PNG binary data).
    region : str
        Voice region.
    afk_timeout : int
        Delay after which users are automatically moved to the afk channel.
    embed_enabled : bool
        Whether the guilds embed is enabled.
    verification_level : int
        The verification level used by the guild.
    mfa_level : int
        The MFA level used by the guild.
    features : list(str)
        Extra features enabled for this guild.
    members : dict(snowflake, :class:`GuildMember`)
        All of the guilds members.
    channels : dict(snowflake, :class:`disco.types.channel.Channel`)
        All of the guilds channels.
    roles : dict(snowflake, :class:`Role`)
        All of the guilds roles.
    emojis : dict(snowflake, :class:`Emoji`)
        All of the guilds emojis.
    voice_states : dict(str, :class:`disco.types.voice.VoiceState`)
        All of the guilds voice states.
    """

    id = snowflake
    owner_id = snowflake
    afk_channel_id = snowflake
    embed_channel_id = snowflake
    name = text
    icon = binary
    splash = binary
    region = str
    afk_timeout = int
    embed_enabled = bool
    verification_level = enum(VerificationLevel)
    mfa_level = int
    features = listof(str)
    members = dictof(GuildMember, key='id')
    channels = dictof(Channel, key='id')
    roles = dictof(Role, key='id')
    emojis = dictof(Emoji, key='id')
    voice_states = dictof(VoiceState, key='session_id')

    def get_permissions(self, user):
        """
        Get the permissions a user has in this guild.

        Returns
        -------
        :class:`disco.types.permissions.PermissionValue`
            Computed permission value for the user.
        """
        if self.owner_id == user.id:
            return PermissionValue(Permissions.ADMINISTRATOR)

        member = self.get_member(user)
        value = PermissionValue(self.roles.get(self.id).permissions)

        for role in map(self.roles.get, member.roles):
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

        for state in self.voice_states.values():
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

    def validate_members(self, ctx):
        if self.members:
            for member in self.members.values():
                member.guild = self
                member.guild_id = self.id

    def validate_channels(self, ctx):
        if self.channels:
            for channel in self.channels.values():
                channel.guild_id = self.id
                channel.guild = self
