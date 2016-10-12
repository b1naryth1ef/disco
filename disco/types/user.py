from holster.enum import Enum

from disco.types.base import SlottedModel, Field, snowflake, text, binary, with_equality, with_hash


class User(SlottedModel, with_equality('id'), with_hash('id')):
    id = Field(snowflake)
    username = Field(text)
    avatar = Field(binary)
    discriminator = Field(str)
    bot = Field(bool)
    verified = Field(bool)
    email = Field(str)

    presence = Field(None)

    @property
    def mention(self):
        return '<@{}>'.format(self.id)

    def to_string(self):
        return '{}#{}'.format(self.username, self.discriminator)

    def __str__(self):
        return '<User {} ({})>'.format(self.id, self.to_string())

    def on_create(self):
        self.client.state.users[self.id] = self


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
    user = Field(User)
    game = Field(Game)
    status = Field(Status)
