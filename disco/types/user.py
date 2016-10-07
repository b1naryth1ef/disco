from disco.types.base import Model, Field, snowflake, text, binary


class User(Model):
    id = Field(snowflake)
    username = Field(text)
    discriminator = Field(str)
    avatar = Field(binary)
    verified = Field(bool)
    email = Field(str)

    def to_string(self):
        return '{}#{}'.format(self.username, self.discriminator)

    def __str__(self):
        return '<User {} ({})>'.format(self.id, self.to_string())

    def on_create(self):
        self.client.state.users[self.id] = self
