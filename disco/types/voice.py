import skema

from disco.types.base import BaseType


class VoiceState(BaseType):
    session_id = skema.StringType()

    guild_id = skema.SnowflakeType()
    channel_id = skema.SnowflakeType()
    user_id = skema.SnowflakeType()

    deaf = skema.BooleanType()
    mute = skema.BooleanType()
    self_deaf = skema.BooleanType()
    self_mute = skema.BooleanType()
    suppress = skema.BooleanType()

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def user(self):
        return self.client.state.users.get(self.user_id)
