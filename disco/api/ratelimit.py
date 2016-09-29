import time
import gevent


class RouteState(object):
    def __init__(self, route, request):
        self.route = route
        self.remaining = 0
        self.reset_time = 0
        self.event = None

        self.update(request)

    @property
    def chilled(self):
        return self.event is not None

    def update(self, request):
        if 'X-RateLimit-Remaining' not in request.headers:
            return

        self.remaining = int(request.headers.get('X-RateLimit-Remaining'))
        self.reset_time = int(request.headers.get('X-RateLimit-Reset'))

    def wait(self, timeout=None):
        self.event.wait(timeout)

    def next_will_ratelimit(self):
        if self.remaining - 1 < 0 and time.time() <= self.reset_time:
            return True

        return False

    def cooldown(self):
        if self.reset_time - time.time() < 0:
            raise Exception('Cannot cooldown for negative time period; check clock sync')

        self.event = gevent.event.Event()
        gevent.sleep((self.reset_time - time.time()) + .5)
        self.event.set()
        self.event = None


class RateLimiter(object):
    def __init__(self):
        self.cooldowns = {}
        self.states = {}

    def check(self, route, timeout=None):
        return self._check(None, timeout) and self._check(route, timeout)

    def _check(self, route, timeout=None):
        if route in self.states:
            # If we're current waiting, join the club
            if self.states[route].chilled:
                return self.states[route].wait(timeout)

            if self.states[route].next_will_ratelimit():
                gevent.spawn(self.states[route].cooldown).wait(timeout)

        return True

    def update(self, route, request):
        if 'X-RateLimit-Global' in request.headers:
            route = None

        if route in self.states:
            self.states[route].update(request)
        else:
            self.states[route] = RouteState(route, request)
