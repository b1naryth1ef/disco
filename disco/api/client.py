from disco.api.http import Routes, HTTPClient

from disco.util.logging import LoggingClass


class APIClient(LoggingClass):
    def __init__(self, client):
        super(APIClient, self).__init__()

        self.client = client
        self.http = HTTPClient(self.client.token)

    def gateway(self, version, encoding):
        r = self.http(Routes.GATEWAY_GET)
        return r['url'] + '?v={}&encoding={}'.format(version, encoding)

    def channels_messages_send(self, channel, content, nonce=None, tts=False):
        r = self.http(Routes.CHANNELS_MESSAGES_POST, channel, json={
                'content': content,
                'nonce': nonce,
                'tts': tts,
            })

        # TODO: return correct types
        return r
