import time
import gevent


class RouteState(object):
    """
    An object which stores ratelimit state for a given method/url route
    combination (as specified in :class:`disco.api.http.Routes`).

    :ivar route: the route this state pertains too
    :ivar remaining: the number of requests remaining before the rate limit is hit
    :ivar reset_time: unix timestamp (in seconds) when this rate limit is reset
    :ivar event: a :class:`gevent.event.Event` used for ratelimit cooldowns
    """
    def __init__(self, route, response):
        self.route = route
        self.remaining = 0
        self.reset_time = 0
        self.event = None

        self.update(response)

    @property
    def chilled(self):
        """
        Whether this route is currently being cooldown (aka waiting until reset_time)
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
        Waits until this route is no longer under a cooldown

        :param timeout: timeout after which waiting will be given up
        """
        self.event.wait(timeout)

    def cooldown(self):
        """
        Waits for the current route to be cooled-down (aka waiting until reset time)
        """
        if self.reset_time - time.time() < 0:
            raise Exception('Cannot cooldown for negative time period; check clock sync')

        self.event = gevent.event.Event()
        gevent.sleep((self.reset_time - time.time()) + .5)
        self.event.set()
        self.event = None


class RateLimiter(object):
    """
    A in-memory store of ratelimit states for all routes we've ever called.

    :ivar states: a Route -> RouteState mapping
    """
    def __init__(self):
        self.states = {}

    def check(self, route, timeout=None):
        """
        Checks whether a given route can be called. This function will return
        immediately if no rate-limit cooldown is being imposed for the given
        route, or will wait indefinently (unless timeout is specified) until
        the route is finished being cooled down. This function should be called
        before making a request to the specified route.

        :param route: route to be checked
        :param timeout: an optional timeout after which we'll stop waiting for
            the cooldown to complete.
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

        :param route: route to update
        :param response: requests response to update the route with
        """
        if 'X-RateLimit-Global' in response.headers:
            route = None

        if route in self.states:
            self.states[route].update(response)
        else:
            self.states[route] = RouteState(route, response)
