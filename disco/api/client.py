from disco.api.http import Routes, HTTPClient
from disco.util.logging import LoggingClass

from disco.types.message import Message
from disco.types.channel import Channel


def optional(**kwargs):
    return {k: v for k, v in kwargs if v is not None}


class APIClient(LoggingClass):
    def __init__(self, client):
        super(APIClient, self).__init__()

        self.client = client
        self.http = HTTPClient(self.client.token)

    def gateway(self, version, encoding):
        data = self.http(Routes.GATEWAY_GET).json()
        return data['url'] + '?v={}&encoding={}'.format(version, encoding)

    def channels_get(self, channel):
        r = self.http(Routes.CHANNELS_GET, channel)
        return Channel.create(self.client, r.json())

    def channels_modify(self, channel, **kwargs):
        r = self.http(Routes.CHANNELS_MODIFY, channel, json=kwargs)
        return Channel.create(self.client, r.json())

    def channels_delete(self, channel):
        r = self.http(Routes.CHANNELS_DELETE, channel)
        return Channel.create(self.client, r.json())

    def channels_messages_list(self, channel, around=None, before=None, after=None, limit=50):
        r = self.http(Routes.CHANNELS_MESSAGES_LIST, channel, json=optional(
            channel=channel,
            around=around,
            before=before,
            after=after,
            limit=limit
        ))

        return [Message.create(self.client, i) for i in r.json()]

    def channels_messages_get(self, channel, message):
        r = self.http(Routes.CHANNELS_MESSAGES_GET, channel, message)
        return Message.create(self.client, r.json())

    def channels_messages_create(self, channel, content, nonce=None, tts=False):
        r = self.http(Routes.CHANNELS_MESSAGES_CREATE, channel, json={
            'content': content,
            'nonce': nonce,
            'tts': tts,
        })

        return Message.create(self.client, r.json())

    def channels_messages_modify(self, channel, message, content):
        r = self.http(Routes.CHANNELS_MESSAGES_MODIFY, channel, message, json={'content': content})
        return Message.create(self.client, r.json())

    def channels_messages_delete(self, channel, message):
        self.http(Routes.CHANNELS_MESSAGES_DELETE, channel, message)

    def channels_messages_delete_bulk(self, channel, messages):
        self.http(Routes.CHANNELS_MESSAGES_DELETE_BULK, channel, json={'messages': messages})
