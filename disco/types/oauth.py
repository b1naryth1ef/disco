from disco.types.base import SlottedModel, Field, ListField, snowflake, text, enum
from disco.types.guild import Integration
from disco.types.user import User
from disco.util.snowflake import to_snowflake


class TeamMembershipState(object):
    INVITED = 1
    ACCEPTED = 2


class TeamMember(SlottedModel):
    membership_state = Field(enum(TeamMembershipState))
    permissions = Field(text)
    team_id = Field(snowflake)
    user = Field(User)


class Team(SlottedModel):
    icon = Field(text)
    id = Field(snowflake)
    members = ListField(TeamMember)
    owner_user_id = Field(snowflake)


class Application(SlottedModel):
    id = Field(snowflake)
    name = Field(text)
    icon = Field(text)
    description = Field(text)
    rpc_origins = ListField(text)
    bot_public = Field(bool)
    bot_require_code_grant = Field(bool)
    owner = Field(User)
    summary = Field(text)
    verify_key = Field(text)
    team = Field(Team)
    guild_id = Field(snowflake)
    primary_sku_id = Field(snowflake)
    slug = Field(text)
    cover_image = Field(text)

    def user_is_owner(self, user):
        user_id = to_snowflake(user)
        if user_id == self.owner.id:
            return True

        return any(user_id == member.user.id for member in self.team.members)

    def get_icon_url(self, fmt='webp', size=1024):
        if not self.icon:
            return ''

        return 'https://cdn.discordapp.com/app-icons/{}/{}.{}?size={}'.format(self.id, self.icon, fmt, size)

    def get_cover_image_url(self, fmt='webp', size=1024):
        if not self.cover_image:
            return ''

        return 'https://cdn.discordapp.com/app-icons/{}/{}.{}?size={}'.format(self.id, self.cover_image, fmt, size)

    @property
    def icon_url(self):
        return self.get_icon_url()

    @property
    def cover_image_url(self):
        return self.get_cover_image_url()


class ConnectionVisibility(object):
    NOBODY = 0
    EVERYONE = 1


class Connection(SlottedModel):
    id = Field(text)
    name = Field(text)
    type = Field(text)
    revoked = Field(bool)
    integrations = ListField(Integration)
    verified = Field(bool)
    friend_sync = Field(bool)
    show_activity = Field(bool)
    visibility = Field(enum(ConnectionVisibility))
