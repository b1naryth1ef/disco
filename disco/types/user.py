from disco.types.base import Model, snowflake, text, binary


class User(Model):
    id = snowflake
    username = text
    discriminator = str
    avatar = binary
    verified = bool
    email = str

    def to_string(self):
        return '{}#{}'.format(self.username, self.discriminator)

    def __str__(self):
        return '<User {} ({})>'.format(self.id, self.to_string())

    def on_create(self):
        self.client.state.users[self.id] = self
