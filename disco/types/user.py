import skema

from disco.types.base import BaseType


class User(BaseType):
    id = skema.SnowflakeType()

    username = skema.StringType()
    discriminator = skema.StringType()
    avatar = skema.BinaryType(None)

    verified = skema.BooleanType(required=False)
    email = skema.EmailType(required=False)

    def to_string(self):
        return '{}#{}'.format(self.username, self.discriminator)

    def __str__(self):
        return '<User {} ({})>'.format(self.id, self.to_string())

    def on_create(self):
        self.client.state.users[self.id] = self
