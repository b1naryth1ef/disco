import re

from disco.types.base import SlottedModel, Field, snowflake
from disco.types.user import User
from disco.util.functional import cached_property


WEBHOOK_URL_RE = re.compile(r'\/api\/webhooks\/(\d+)\/(.[^/]+)')


class Webhook(SlottedModel):
    id = Field(snowflake)
    guild_id = Field(snowflake)
    channel_id = Field(snowflake)
    user = Field(User)
    name = Field(str)
    avatar = Field(str)
    token = Field(str)

    @classmethod
    def execute_url(cls, url, **kwargs):
        from disco.api.client import APIClient

        results = WEBHOOK_URL_RE.findall(url)
        if len(results) != 1:
            return Exception('Invalid Webhook URL')

        return cls(id=results[0][0], token=results[0][1]).execute(
            client=APIClient(None),
            **kwargs
        )

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

    def execute(self, content=None, username=None, avatar_url=None, tts=False, fobj=None, embeds=[], wait=False, client=None):
        # TODO: support file stuff properly
        client = client or self.client.api

        return client.webhooks_token_execute(self.id, self.token, {
            'content': content,
            'username': username,
            'avatar_url': avatar_url,
            'tts': tts,
            'file': fobj,
            'embeds': [i.to_dict() for i in embeds],
        }, wait)
