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
