from disco.types.base import Model, Field, snowflake


class VoiceState(Model):
    session_id = Field(str)
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    user_id = Field(snowflake)
    deaf = Field(bool)
    mute = Field(bool)
    self_deaf = Field(bool)
    self_mute = Field(bool)
    suppress = Field(bool)

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def user(self):
        return self.client.state.users.get(self.user_id)
