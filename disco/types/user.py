import skema


class User(skema.Model):
    id = skema.SnowflakeType()

    username = skema.StringType()
    discriminator = skema.StringType()
    avatar = skema.BinaryType(None)

    verified = skema.BooleanType(required=False)
    email = skema.EmailType(required=False)
