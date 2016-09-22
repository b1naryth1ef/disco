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
    # Gateway
    GATEWAY_GET = (HTTPMethod.GET, '/gateway')

    # Channels
    CHANNELS_GET = (HTTPMethod.GET, '/channels/{}')
    CHANNELS_MODIFY= (HTTPMethod.PATCH, '/channels/{}')
    CHANNELS_DELETE = (HTTPMethod.DELETE, '/channels/{}')

    CHANNELS_MESSAGES_LIST = (HTTPMethod.GET, '/channels/{}/messages')
    CHANNELS_MESSAGES_GET = (HTTPMethod.GET, '/channels/{}/messages/{}')
    CHANNELS_MESSAGES_CREATE = (HTTPMethod.POST, '/channels/{}/messages')
    CHANNELS_MESSAGES_MODFIY = (HTTPMethod.PATCH, '/channels/{}/messages/{}')
    CHANNELS_MESSAGES_DELETE = (HTTPMethod.DELETE, '/channels/{}/messages/{}')
    CHANNELS_MESSAGES_DELETE_BULK = (HTTPMethod.POST, '/channels/{}/messages/bulk_delete')

    CHANNELS_PERMISSIONS_MODIFY = (HTTPMethod.PUT, '/channels/{}/permissions/{}')
    CHANNELS_PERMISSIONS_DELETE = (HTTPMethod.DELETE, '/channels/{}/permissions/{}')
    CHANNELS_INVITES_LIST = (HTTPMethod.GET, '/channels/{}/invites')
    CHANNELS_INVITES_CREATE = (HTTPMethod.POST, '/channels/{}/invites')

    CHANNELS_PINS_LIST = (HTTPMethod.GET, '/channels/{}/pins')
    CHANNELS_PINS_CREATE = (HTTPMethod.PUT, '/channels/{}/pins/{}')
    CHANNELS_PINS_DELETE = (HTTPMethod.DELETE, '/channels/{}/pins/{}')

    # Guilds
    GUILDS_GET = (HTTPMethod.GET, '/guilds/{}')
    GUILDS_MODIFY = (HTTPMethod.PATCH, '/guilds/{}')
    GUILDS_DELETE = (HTTPMethod.DELETE, '/guilds/{}')
    GUILDS_CHANNELS_LIST = (HTTPMethod.GET, '/guilds/{}/channels')
    GUILDS_CHANNELS_CREATE = (HTTPMethod.POST, '/guilds/{}/channels')
    GUILDS_CHANNELS_MODIFY = (HTTPMethod.PATCH, '/guilds/{}/channels')
    GUILDS_MEMBERS_LIST = (HTTPMethod.GET, '/guilds/{}/members')
    GUILDS_MEMBERS_GET = (HTTPMethod.GET, '/guilds/{}/members/{}')
    GUILDS_MEMBERS_MODIFY = (HTTPMethod.PATCH, '/guilds/{}/members/{}')
    GUILDS_MEMBERS_KICK = (HTTPMethod.DELETE, '/guilds/{}/members/{}')
    GUILDS_BANS_LIST = (HTTPMethod.GET, '/guilds/{}/bans')
    GUILDS_BANS_CREATE = (HTTPMethod.PUT, '/guilds/{}/bans/{}')
    GUILDS_BANS_DELETE = (HTTPMethod.DELETE, '/guilds/{}/bans/{}')
    GUILDS_ROLES_LIST = (HTTPMethod.GET, '/guilds/{}/roles')
    GUILDS_ROLES_CREATE = (HTTPMethod.GET, '/guilds/{}/roles')
    GUILDS_ROLES_MODIFY_BATCH = (HTTPMethod.PATCH, '/guilds/{}/roles')
    GUILDS_ROLES_MODIFY = (HTTPMethod.PATCH, '/guilds/{}/roles/{}')
    GUILDS_ROLES_DELETE = (HTTPMethod.DELETE, '/guilds/{}/roles/{}')
    GUILDS_PRUNE_COUNT = (HTTPMethod.GET, '/guilds/{}/prune')
    GUILDS_PRUNE_BEGIN = (HTTPMethod.POST, '/guilds/{}/prune')
    GUILDS_VOICE_REGIONS_LIST = (HTTPMethod.GET, '/guilds/{}/regions')
    GUILDS_INVITES_LIST = (HTTPMethod.GET, '/guilds/{}/invites')
    GUILDS_INTEGRATIONS_LIST = (HTTPMethod.GET, '/guilds/{}/integrations')
    GUILDS_INTEGRATIONS_CREATE = (HTTPMethod.POST, '/guilds/{}/integrations')
    GUILDS_INTEGRATIONS_MODIFY = (HTTPMethod.PATCH, '/guilds/{}/integrations/{}')
    GUILDS_INTEGRATIONS_DELETE = (HTTPMethod.DELETE, '/guilds/{}/integrations/{}')
    GUILDS_INTEGRATIONS_SYNC = (HTTPMethod.POST, '/guilds/{}/integrations/{}/sync')
    GUILDS_EMBED_GET = (HTTPMethod.GET, '/guilds/{}/embed')
    GUILDS_EMBED_MODIFY = (HTTPMethod.PATCH, '/guilds/{}/embed')

    # Users
    USERS_ME_GET = (HTTPMethod.GET, '/users/@me')
    USERS_ME_PATCH = (HTTPMethod.PATCH, '/users/@me')
    USERS_ME_GUILDS_LIST = (HTTPMethod.GET, '/users/@me/guilds')
    USERS_ME_GUILDS_LEAVE = (HTTPMethod.DELETE, '/users/@me/guilds/{}')
    USERS_ME_DMS_LIST = (HTTPMethod.GET, '/users/@me/channels')
    USERS_ME_DMS_CREATE = (HTTPMethod.POST, '/users/@me/channels')
    USERS_ME_CONNECTIONS_LIST = (HTTPMethod.GET, '/users/@me/connections')
    USERS_GET = (HTTPMethod.GET, '/users/{}')


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
            return r
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
