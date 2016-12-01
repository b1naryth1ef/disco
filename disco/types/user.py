from holster.enum import Enum

from disco.types.base import SlottedModel, Field, snowflake, text, binary, with_equality, with_hash


class User(SlottedModel, with_equality('id'), with_hash('id')):
    id = Field(snowflake)
    username = Field(text)
    avatar = Field(binary)
    discriminator = Field(str)
    bot = Field(bool, default=False)
    verified = Field(bool)
    email = Field(str)

    presence = Field(None)

    @property
    def avatar_url(self):
        if not self.avatar:
            return None

        return 'https://discordapp.com/api/users/{}/avatars/{}.jpg'.format(
            self.id,
            self.avatar)

    @property
    def mention(self):
        return '<@{}>'.format(self.id)

    def __str__(self):
        return u'{}#{}'.format(self.username, str(self.discriminator).zfill(4))

    def __repr__(self):
        return u'<User {} ({})>'.format(self.id, self)


GameType = Enum(
    DEFAULT=0,
    STREAMING=1,
)

Status = Enum(
    'ONLINE',
    'IDLE',
    'DND',
    'INVISIBLE',
    'OFFLINE'
)


class Game(SlottedModel):
    type = Field(GameType)
    name = Field(text)
    url = Field(text)


class Presence(SlottedModel):
    user = Field(User, alias='user', ignore_dump=['presence'])
    game = Field(Game)
    status = Field(Status)
