from disco.types.base import Model, snowflake


class VoiceState(Model):
    session_id = str
    guild_id = snowflake
    channel_id = snowflake
    user_id = snowflake
    deaf = bool
    mute = bool
    self_deaf = bool
    self_mute = bool
    suppress = bool

    @property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)

    @property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def user(self):
        return self.client.state.users.get(self.user_id)
