import requests

from holster.enum import Enum

HTTPMethod = Enum(
    GET='GET',
    POST='POST',
    PUT='PUT',
    PATCH='PATCH',
    DELETE='DELETE',
)


class Routes(object):
    USERS_ME_GET = (HTTPMethod.GET, '/users/@me')
    USERS_ME_PATCH = (HTTPMethod.PATCH, '/users/@me')

    GATEWAY_GET = (HTTPMethod.GET, '/gateway')

    CHANNELS_MESSAGES_POST = (HTTPMethod.POST, '/channels/{}/messages')


class APIException(Exception):
    def __init__(self, obj):
        self.code = obj['code']
        self.msg = obj['msg']

        super(APIException, self).__init__(self.msg)


class HTTPClient(object):
    BASE_URL = 'https://discordapp.com/api'

    def __init__(self, token):
        self.headers = {
            'Authorization': 'Bot ' + token,
        }

    def __call__(self, route, *args, **kwargs):
        method, url = route

        kwargs['headers'] = self.headers

        r = requests.request(str(method), (self.BASE_URL + url).format(*args), **kwargs)

        try:
            r.raise_for_status()
        except:
            print r.json()
            raise
            # TODO: rate limits
            # TODO: check json
            raise APIException(r.json())

        # TODO: check json
        return r.json()
