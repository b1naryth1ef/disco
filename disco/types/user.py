from holster.enum import Enum

from disco.types.base import SlottedModel, Field, snowflake, text, with_equality, with_hash

DefaultAvatars = Enum(
    BLURPLE=0,
    GREY=1,
    GREEN=2,
    ORANGE=3,
    RED=4,
)


class User(SlottedModel, with_equality('id'), with_hash('id')):
    id = Field(snowflake)
    username = Field(text)
    avatar = Field(text)
    discriminator = Field(text)
    bot = Field(bool, default=False)
    verified = Field(bool)
    email = Field(text)

    presence = Field(None)

    def get_avatar_url(self, fmt=None, size=1024):
        if not self.avatar:
            return 'https://cdn.discordapp.com/embed/avatars/{}.png'.format(self.default_avatar.value)
        if fmt is not None:
            return 'https://cdn.discordapp.com/avatars/{}/{}.{}?size={}'.format(self.id, self.avatar, fmt, size)
        if self.avatar.startswith('a_'):
            return 'https://cdn.discordapp.com/avatars/{}/{}.gif?size={}'.format(self.id, self.avatar, size)
        else:
            return 'https://cdn.discordapp.com/avatars/{}/{}.webp?size={}'.format(self.id, self.avatar, size)

    @property
    def default_avatar(self):
        return DefaultAvatars[int(self.discriminator) % len(DefaultAvatars.attrs)]

    @property
    def avatar_url(self):
        return self.get_avatar_url()

    @property
    def mention(self):
        return '<@{}>'.format(self.id)

    def open_dm(self):
        return self.client.api.users_me_dms_create(self.id)

    def __str__(self):
        return u'{}#{}'.format(self.username, str(self.discriminator).zfill(4))

    def __repr__(self):
        return u'<User {} ({})>'.format(self.id, self)


GameType = Enum(
    DEFAULT=0,
    STREAMING=1,
    LISTENING=2,
    WATCHING=3,
)

Status = Enum(
    'ONLINE',
    'IDLE',
    'DND',
    'INVISIBLE',
    'OFFLINE',
)


class Game(SlottedModel):
    type = Field(GameType)
    name = Field(text)
    url = Field(text)


class Presence(SlottedModel):
    user = Field(User, alias='user', ignore_dump=['presence'])
    game = Field(Game)
    status = Field(Status)
