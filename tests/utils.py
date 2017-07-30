import time
import random

from disco.api.client import APIClient as _APIClient
from disco.util.snowflake import from_timestamp_ms


class CallContainer(object):
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class APIClient(_APIClient):
    def __init__(self):
        self.client = None
        self.http = CallContainer()


def random_snowflake():
    return from_timestamp_ms(
        (time.time() * 1000.0) + random.randint(1, 9999)
    )
