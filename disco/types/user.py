import skema

from disco.types.base import BaseType


class User(BaseType):
    id = skema.SnowflakeType()

    username = skema.StringType()
    discriminator = skema.StringType()
    avatar = skema.BinaryType(None)

    verified = skema.BooleanType(required=False)
    email = skema.EmailType(required=False)

    def on_create(self):
        self.client.state.users[self.id] = self
