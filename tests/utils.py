import time
import contextlib
from disco.api.client import APIClient


class CallContainer(object):
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class TestAPIClient(APIClient):
    def __init__(self):
        self.client = None
        self.http = CallContainer()


def bench(times, func):
    main_start = time.time()

    worst = None
    best = None

    for _ in range(times):
        start = time.time()
        func()
        dur = time.time() - start

        if not worst or dur > worst:
            worst = dur

        if not best or dur < best:
            best = dur

    main_dur = time.time() - main_start
    return main_dur, worst, best
