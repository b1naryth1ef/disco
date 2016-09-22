import logging

from disco.api.client import APIClient
from disco.gateway.client import GatewayClient

log = logging.getLogger(__name__)


class DiscoClient(object):
    def __init__(self, token, sharding=None):
        self.log = log
        self.token = token
        self.sharding = sharding or {'number': 0, 'total': 1}

        self.api = APIClient(self)
        self.gw = GatewayClient(self)

    def run(self):
        return self.gw.run()

    def run_forever(self):
        return self.gw.run().join()
