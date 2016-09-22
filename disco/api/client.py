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
