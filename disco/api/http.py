import requests
import random
import gevent
import six
import sys

from holster.enum import Enum

from disco import VERSION as disco_version
from requests import __version__ as requests_version
from disco.util.logging import LoggingClass
from disco.api.ratelimit import RateLimiter

# Enum of all HTTP methods used
HTTPMethod = Enum(
    GET='GET',
    POST='POST',
    PUT='PUT',
    PATCH='PATCH',
    DELETE='DELETE',
)


def to_bytes(obj):
    if six.PY2:
        if isinstance(obj, six.text_type):
            return obj.encode('utf-8')
    return obj


class Routes(object):
    """
    Simple Python object-enum of all method/url route combinations available to
    this client.
    """
    # Gateway
    GATEWAY_GET = (HTTPMethod.GET, '/gateway')
    GATEWAY_BOT_GET = (HTTPMethod.GET, '/gateway/bot')

    # Channels
    CHANNELS = '/channels/{channel}'
    CHANNELS_GET = (HTTPMethod.GET, CHANNELS)
    CHANNELS_MODIFY = (HTTPMethod.PATCH, CHANNELS)
    CHANNELS_DELETE = (HTTPMethod.DELETE, CHANNELS)
    CHANNELS_TYPING = (HTTPMethod.POST, CHANNELS + '/typing')
    CHANNELS_MESSAGES_LIST = (HTTPMethod.GET, CHANNELS + '/messages')
    CHANNELS_MESSAGES_GET = (HTTPMethod.GET, CHANNELS + '/messages/{message}')
    CHANNELS_MESSAGES_CREATE = (HTTPMethod.POST, CHANNELS + '/messages')
    CHANNELS_MESSAGES_MODIFY = (HTTPMethod.PATCH, CHANNELS + '/messages/{message}')
    CHANNELS_MESSAGES_DELETE = (HTTPMethod.DELETE, CHANNELS + '/messages/{message}')
    CHANNELS_MESSAGES_DELETE_BULK = (HTTPMethod.POST, CHANNELS + '/messages/bulk_delete')
    CHANNELS_MESSAGES_REACTIONS_GET = (HTTPMethod.GET, CHANNELS + '/messages/{message}/reactions/{emoji}')
    CHANNELS_MESSAGES_REACTIONS_CREATE = (HTTPMethod.PUT, CHANNELS + '/messages/{message}/reactions/{emoji}/@me')
    CHANNELS_MESSAGES_REACTIONS_DELETE_ME = (HTTPMethod.DELETE, CHANNELS + '/messages/{message}/reactions/{emoji}/@me')
    CHANNELS_MESSAGES_REACTIONS_DELETE_USER = (HTTPMethod.DELETE,
                                               CHANNELS + '/messages/{message}/reactions/{emoji}/{user}')
    CHANNELS_PERMISSIONS_MODIFY = (HTTPMethod.PUT, CHANNELS + '/permissions/{permission}')
    CHANNELS_PERMISSIONS_DELETE = (HTTPMethod.DELETE, CHANNELS + '/permissions/{permission}')
    CHANNELS_INVITES_LIST = (HTTPMethod.GET, CHANNELS + '/invites')
    CHANNELS_INVITES_CREATE = (HTTPMethod.POST, CHANNELS + '/invites')
    CHANNELS_PINS_LIST = (HTTPMethod.GET, CHANNELS + '/pins')
    CHANNELS_PINS_CREATE = (HTTPMethod.PUT, CHANNELS + '/pins/{pin}')
    CHANNELS_PINS_DELETE = (HTTPMethod.DELETE, CHANNELS + '/pins/{pin}')
    CHANNELS_WEBHOOKS_CREATE = (HTTPMethod.POST, CHANNELS + '/webhooks')
    CHANNELS_WEBHOOKS_LIST = (HTTPMethod.GET, CHANNELS + '/webhooks')

    # Guilds
    GUILDS = '/guilds/{guild}'
    GUILDS_GET = (HTTPMethod.GET, GUILDS)
    GUILDS_MODIFY = (HTTPMethod.PATCH, GUILDS)
    GUILDS_DELETE = (HTTPMethod.DELETE, GUILDS)
    GUILDS_CHANNELS_LIST = (HTTPMethod.GET, GUILDS + '/channels')
    GUILDS_CHANNELS_CREATE = (HTTPMethod.POST, GUILDS + '/channels')
    GUILDS_CHANNELS_MODIFY = (HTTPMethod.PATCH, GUILDS + '/channels')
    GUILDS_MEMBERS_LIST = (HTTPMethod.GET, GUILDS + '/members')
    GUILDS_MEMBERS_GET = (HTTPMethod.GET, GUILDS + '/members/{member}')
    GUILDS_MEMBERS_MODIFY = (HTTPMethod.PATCH, GUILDS + '/members/{member}')
    GUILDS_MEMBERS_ROLES_ADD = (HTTPMethod.PUT, GUILDS + '/members/{member}/roles/{role}')
    GUILDS_MEMBERS_ROLES_REMOVE = (HTTPMethod.DELETE, GUILDS + '/members/{member}/roles/{role}')
    GUILDS_MEMBERS_ME_NICK = (HTTPMethod.PATCH, GUILDS + '/members/@me/nick')
    GUILDS_MEMBERS_KICK = (HTTPMethod.DELETE, GUILDS + '/members/{member}')
    GUILDS_BANS_LIST = (HTTPMethod.GET, GUILDS + '/bans')
    GUILDS_BANS_CREATE = (HTTPMethod.PUT, GUILDS + '/bans/{user}')
    GUILDS_BANS_DELETE = (HTTPMethod.DELETE, GUILDS + '/bans/{user}')
    GUILDS_ROLES_LIST = (HTTPMethod.GET, GUILDS + '/roles')
    GUILDS_ROLES_CREATE = (HTTPMethod.POST, GUILDS + '/roles')
    GUILDS_ROLES_MODIFY_BATCH = (HTTPMethod.PATCH, GUILDS + '/roles')
    GUILDS_ROLES_MODIFY = (HTTPMethod.PATCH, GUILDS + '/roles/{role}')
    GUILDS_ROLES_DELETE = (HTTPMethod.DELETE, GUILDS + '/roles/{role}')
    GUILDS_PRUNE_COUNT = (HTTPMethod.GET, GUILDS + '/prune')
    GUILDS_PRUNE_BEGIN = (HTTPMethod.POST, GUILDS + '/prune')
    GUILDS_VOICE_REGIONS_LIST = (HTTPMethod.GET, GUILDS + '/regions')
    GUILDS_INVITES_LIST = (HTTPMethod.GET, GUILDS + '/invites')
    GUILDS_INTEGRATIONS_LIST = (HTTPMethod.GET, GUILDS + '/integrations')
    GUILDS_INTEGRATIONS_CREATE = (HTTPMethod.POST, GUILDS + '/integrations')
    GUILDS_INTEGRATIONS_MODIFY = (HTTPMethod.PATCH, GUILDS + '/integrations/{integration}')
    GUILDS_INTEGRATIONS_DELETE = (HTTPMethod.DELETE, GUILDS + '/integrations/{integration}')
    GUILDS_INTEGRATIONS_SYNC = (HTTPMethod.POST, GUILDS + '/integrations/{integration}/sync')
    GUILDS_EMBED_GET = (HTTPMethod.GET, GUILDS + '/embed')
    GUILDS_EMBED_MODIFY = (HTTPMethod.PATCH, GUILDS + '/embed')
    GUILDS_WEBHOOKS_LIST = (HTTPMethod.GET, GUILDS + '/webhooks')
    GUILDS_EMOJIS_LIST = (HTTPMethod.GET, GUILDS + '/emojis')
    GUILDS_EMOJIS_CREATE = (HTTPMethod.POST, GUILDS + '/emojis')
    GUILDS_EMOJIS_MODIFY = (HTTPMethod.PATCH, GUILDS + '/emojis/{emoji}')
    GUILDS_EMOJIS_DELETE = (HTTPMethod.DELETE, GUILDS + '/emojis/{emoji}')
    GUILDS_AUDITLOGS_LIST = (HTTPMethod.GET, GUILDS + '/audit-logs')

    # Users
    USERS = '/users'
    USERS_ME_GET = (HTTPMethod.GET, USERS + '/@me')
    USERS_ME_PATCH = (HTTPMethod.PATCH, USERS + '/@me')
    USERS_ME_GUILDS_LIST = (HTTPMethod.GET, USERS + '/@me/guilds')
    USERS_ME_GUILDS_DELETE = (HTTPMethod.DELETE, USERS + '/@me/guilds/{guild}')
    USERS_ME_DMS_LIST = (HTTPMethod.GET, USERS + '/@me/channels')
    USERS_ME_DMS_CREATE = (HTTPMethod.POST, USERS + '/@me/channels')
    USERS_ME_CONNECTIONS_LIST = (HTTPMethod.GET, USERS + '/@me/connections')
    USERS_GET = (HTTPMethod.GET, USERS + '/{user}')

    # Invites
    INVITES = '/invites'
    INVITES_GET = (HTTPMethod.GET, INVITES + '/{invite}')
    INVITES_DELETE = (HTTPMethod.DELETE, INVITES + '/{invite}')

    # Webhooks
    WEBHOOKS = '/webhooks/{webhook}'
    WEBHOOKS_GET = (HTTPMethod.GET, WEBHOOKS)
    WEBHOOKS_MODIFY = (HTTPMethod.PATCH, WEBHOOKS)
    WEBHOOKS_DELETE = (HTTPMethod.DELETE, WEBHOOKS)
    WEBHOOKS_TOKEN_GET = (HTTPMethod.GET, WEBHOOKS + '/{token}')
    WEBHOOKS_TOKEN_MODIFY = (HTTPMethod.PATCH, WEBHOOKS + '/{token}')
    WEBHOOKS_TOKEN_DELETE = (HTTPMethod.DELETE, WEBHOOKS + '/{token}')
    WEBHOOKS_TOKEN_EXECUTE = (HTTPMethod.POST, WEBHOOKS + '/{token}')


class APIResponse(object):
    def __init__(self):
        self.response = None
        self.exception = None
        self.rate_limited_duration = 0


class APIException(Exception):
    """
    Exception thrown when an HTTP-client level error occurs. Usually this will
    be a non-success status-code, or a transient network issue.

    Attributes
    ----------
    status_code : int
        The status code returned by the API for the request that triggered this
        error.
    """
    def __init__(self, response, retries=None):
        self.response = response
        self.retries = retries

        self.code = 0
        self.msg = 'Request Failed ({})'.format(response.status_code)
        self.errors = {}

        if self.retries:
            self.msg += " after {} retries".format(self.retries)

        # Try to decode JSON, and extract params
        try:
            data = self.response.json()

            if 'code' in data:
                self.code = data['code']
                self.errors = data.get('errors', {})
                self.msg = '{} ({} - {})'.format(data['message'], self.code, self.errors)
            elif len(data) == 1:
                key, value = list(data.items())[0]
                self.msg = 'Request Failed: {}: {}'.format(key, ', '.join(value))
        except ValueError:
            pass

        # DEPRECATED: left for backwards compat
        self.status_code = response.status_code
        self.content = response.content

        super(APIException, self).__init__(self.msg)


class HTTPClient(LoggingClass):
    """
    A simple HTTP client which wraps the requests library, adding support for
    Discords rate-limit headers, authorization, and request/response validation.
    """
    BASE_URL = 'https://discordapp.com/api/v7'
    MAX_RETRIES = 5

    def __init__(self, token, after_request=None):
        super(HTTPClient, self).__init__()

        py_version = '{}.{}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro)

        self.limiter = RateLimiter()
        self.headers = {
            'User-Agent': 'DiscordBot (https://github.com/b1naryth1ef/disco {}) Python/{} requests/{}'.format(
                disco_version,
                py_version,
                requests_version),
        }

        if token:
            self.headers['Authorization'] = 'Bot ' + token

        self.after_request = after_request
        self.session = requests.Session()

    def __call__(self, route, args=None, **kwargs):
        return self.call(route, args, **kwargs)

    def call(self, route, args=None, **kwargs):
        """
        Makes a request to the given route (as specified in
        :class:`disco.api.http.Routes`) with a set of URL arguments, and keyword
        arguments passed to requests.

        Parameters
        ----------
        route : tuple(:class:`HTTPMethod`, str)
            The method.URL combination that when compiled with URL arguments
            creates a requestable route which the HTTPClient will make the
            request too.
        args : dict(str, str)
            A dictionary of URL arguments that will be compiled with the raw URL
            to create the requestable route. The HTTPClient uses this to track
            rate limits as well.
        kwargs : dict
            Keyword arguments that will be passed along to the requests library

        Raises
        ------
        APIException
            Raised when an unrecoverable error occurs, or when we've exhausted
            the number of retries.

        Returns
        -------
        :class:`requests.Response`
            The response object for the request
        """
        args = args or {}
        retry = kwargs.pop('retry_number', 0)

        # Merge or set headers
        if 'headers' in kwargs:
            kwargs['headers'].update(self.headers)
        else:
            kwargs['headers'] = self.headers

        # Build the bucket URL
        args = {k: to_bytes(v) for k, v in six.iteritems(args)}
        filtered = {k: (v if k in ('guild', 'channel') else '') for k, v in six.iteritems(args)}
        bucket = (route[0].value, route[1].format(**filtered))

        response = APIResponse()

        # Possibly wait if we're rate limited
        response.rate_limited_duration = self.limiter.check(bucket)

        self.log.debug('KW: %s', kwargs)

        # Make the actual request
        url = self.BASE_URL + route[1].format(**args)
        self.log.info('%s %s (%s)', route[0].value, url, kwargs.get('params'))
        r = self.session.request(route[0].value, url, **kwargs)

        if self.after_request:
            response.response = r
            self.after_request(response)

        # Update rate limiter
        self.limiter.update(bucket, r)

        # If we got a success status code, just return the data
        if r.status_code < 400:
            return r
        elif r.status_code != 429 and 400 <= r.status_code < 500:
            self.log.warning('Request failed with code %s: %s', r.status_code, r.content)
            response.exception = APIException(r)
            raise response.exception
        else:
            if r.status_code == 429:
                self.log.warning(
                    'Request responded w/ 429, retrying (but this should not happen, check your clock sync')

            # If we hit the max retries, throw an error
            retry += 1
            if retry > self.MAX_RETRIES:
                self.log.error('Failing request, hit max retries')
                raise APIException(r, retries=self.MAX_RETRIES)

            backoff = self.random_backoff()
            self.log.warning('Request to `{}` failed with code {}, retrying after {}s ({})'.format(
                url, r.status_code, backoff, r.content
            ))
            gevent.sleep(backoff)

            # Otherwise just recurse and try again
            return self(route, args, retry_number=retry, **kwargs)

    @staticmethod
    def random_backoff():
        """
        Returns a random backoff (in milliseconds) to be used for any error the
        client suspects is transient. Will always return a value between 500 and
        5000 milliseconds.

        :returns: a random backoff in milliseconds
        :rtype: float
        """
        return random.randint(500, 5000) / 1000.0
