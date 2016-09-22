import requests

from holster.enum import Enum

from disco.util.logging import LoggingClass
from disco.api.ratelimit import RateLimiter

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
    def __init__(self, msg, status_code=0, content=None):
        super(APIException, self).__init__(msg)
        self.status_code = status_code
        self.content = content


class HTTPClient(LoggingClass):
    BASE_URL = 'https://discordapp.com/api'
    MAX_RETRIES = 5

    def __init__(self, token):
        super(HTTPClient, self).__init__()

        self.limiter = RateLimiter()
        self.headers = {
            'Authorization': 'Bot ' + token,
        }

    def __call__(self, route, *args, **kwargs):
        retry = kwargs.pop('retry_number', 0)

        # Merge or set headers
        if 'headers' in kwargs:
            kwargs['headers'].update(self.headers)
        else:
            kwargs['headers'] = self.headers

        # Compile URL args
        compiled = (str(route[0]), (self.BASE_URL) + route[1].format(*args))

        # Possibly wait if we're rate limited
        self.limiter.check(compiled)

        # Make the actual request
        r = requests.request(compiled[0], compiled[1], **kwargs)

        # Update rate limiter
        self.limiter.update(compiled, r)

        # If we got a success status code, just return the data
        if r.status_code < 400:
            return r.json()
        else:
            if r.status_code == 429:
                self.log.warning('Request responded w/ 429, retrying (but this should not happen, check your clock sync')

            # If we hit the max retries, throw an error
            retry += 1
            if retry > self.MAX_RETRIES:
                self.log.error('Failing request, hit max retries')
                raise APIException('Request failed after {} attempts'.format(self.MAX_RETRIES), r.status_code, r.content)

            # Otherwise just recurse and try again
            return self(route, retry_number=retry, *args, **kwargs)
