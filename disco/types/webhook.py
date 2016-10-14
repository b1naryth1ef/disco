from disco.types.base import SlottedModel, Field, snowflake
from disco.types.user import User
from disco.util.functional import cached_property


class Webhook(SlottedModel):
    id = Field(snowflake)
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    user = Field(User)
    name = Field(str)
    avatar = Field(str)
    token = Field(str)

    @cached_property
    def guild(self):
        return self.client.state.guilds.get(self.guild_id)

    @cached_property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    def delete(self):
        if self.token:
            self.client.api.webhooks_token_delete(self.id, self.token)
        else:
            self.client.api.webhooks_delete(self.id)

    def modify(self, name, avatar):
        if self.token:
            return self.client.api.webhooks_token_modify(self.id, self.token, name, avatar)
        else:
            return self.client.api.webhooks_modify(self.id, name, avatar)

    def execute(self, content=None, username=None, avatar_url=None, tts=False, file=None, embeds=[], wait=False):
        return self.client.api.webhooks_token_execute(self.id, self.token, {
            'content': content,
            'username': username,
            'avatar_url': avatar_url,
            'tts': tts,
            'file': file,
            'embeds': [i.to_dict() for i in embeds],
        }, wait)
