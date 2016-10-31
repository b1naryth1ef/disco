import time
import gevent

from disco.util.logging import LoggingClass


class RouteState(LoggingClass):
    """
    An object which stores ratelimit state for a given method/url route
    combination (as specified in :class:`disco.api.http.Routes`).

    Parameters
    ----------
    route : tuple(HTTPMethod, str)
        The route which this RouteState is for.
    response : :class:`requests.Response`
        The response object for the last request made to the route, should contain
        the standard rate limit headers.

    Attributes
    ---------
    route : tuple(HTTPMethod, str)
        The route which this RouteState is for.
    remaining : int
        The number of remaining requests to the route before the rate limit will
        be hit, triggering a 429 response.
    reset_time : int
        A unix epoch timestamp (in seconds) after which this rate limit is reset
    event : :class:`gevent.event.Event`
        An event that is used to block all requests while a route is in the
        cooldown stage.
    """
    def __init__(self, route, response):
        self.route = route
        self.remaining = 0
        self.reset_time = 0
        self.event = None

        self.update(response)

    def __repr__(self):
        return '<RouteState {}>'.format(' '.join(self.route))

    @property
    def chilled(self):
        """
        Whether this route is currently being cooldown (aka waiting until reset_time).
        """
        return self.event is not None

    @property
    def next_will_ratelimit(self):
        """
        Whether the next request to the route (at this moment in time) will
        trigger the rate limit.
        """

        if self.remaining - 1 < 0 and time.time() <= self.reset_time:
            return True

        return False

    def update(self, response):
        """
        Updates this route with a given Requests response object. Its expected
        the response has the required headers, however in the case it doesn't
        this function has no effect.
        """
        if 'X-RateLimit-Remaining' not in response.headers:
            return

        self.remaining = int(response.headers.get('X-RateLimit-Remaining'))
        self.reset_time = int(response.headers.get('X-RateLimit-Reset'))

    def wait(self, timeout=None):
        """
        Waits until this route is no longer under a cooldown.

        Parameters
        ----------
        timeout : Optional[int]
            A timeout (in seconds) after which we will give up waiting


        Returns
        -------
        bool
            False if the timeout period expired before the cooldown was finished.
        """
        return self.event.wait(timeout)

    def cooldown(self):
        """
        Waits for the current route to be cooled-down (aka waiting until reset time).
        """
        if self.reset_time - time.time() < 0:
            raise Exception('Cannot cooldown for negative time period; check clock sync')

        self.event = gevent.event.Event()
        delay = (self.reset_time - time.time()) + .5
        self.log.debug('Cooling down bucket %s for %s seconds', self, delay)
        gevent.sleep(delay)
        self.event.set()
        self.event = None


class RateLimiter(LoggingClass):
    """
    A in-memory store of ratelimit states for all routes we've ever called.

    Attributes
    ----------
    states : dict(tuple(HTTPMethod, str), :class:`RouteState`)
        Contains a :class:`RouteState` for each route the RateLimiter is currently
        tracking.
    """
    def __init__(self):
        self.states = {}

    def check(self, route, timeout=None):
        """
        Checks whether a given route can be called. This function will return
        immediately if no rate-limit cooldown is being imposed for the given
        route, or will wait indefinitely (unless timeout is specified) until
        the route is finished being cooled down. This function should be called
        before making a request to the specified route.

        Parameters
        ----------
        route : tuple(HTTPMethod, str)
            The route that will be checked.
        timeout : Optional[int]
            A timeout after which we'll give up waiting for a route's cooldown
            to expire, and immediately return.

        Returns
        -------
        bool
            False if the timeout period expired before the route finished cooling
            down.
        """
        return self._check(None, timeout) and self._check(route, timeout)

    def _check(self, route, timeout=None):
        if route in self.states:
            # If we're current waiting, join the club
            if self.states[route].chilled:
                return self.states[route].wait(timeout)

            if self.states[route].next_will_ratelimit:
                gevent.spawn(self.states[route].cooldown).get(True, timeout)

        return True

    def update(self, route, response):
        """
        Updates the given routes state with the rate-limit headers inside the
        response from a previous call to the route.

        Parameters
        ---------
        route : tuple(HTTPMethod, str)
            The route that will be updated.
        response : :class:`requests.Response`
            The response object for the last request to the route, whose headers
            will be used to update the routes rate limit state.
        """
        if 'X-RateLimit-Global' in response.headers:
            route = None

        if route in self.states:
            self.states[route].update(response)
        else:
            self.states[route] = RouteState(route, response)
