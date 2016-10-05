import logging
import gevent

from holster.emitter import Emitter

from disco.state import State
from disco.api.client import APIClient
from disco.gateway.client import GatewayClient

log = logging.getLogger(__name__)


class DiscoClient(object):
    def __init__(self, token, sharding=None):
        self.log = log
        self.token = token
        self.sharding = sharding or {'number': 0, 'total': 1}

        self.events = Emitter(gevent.spawn)
        self.packets = Emitter(gevent.spawn)

        self.state = State(self)
        self.api = APIClient(self)
        self.gw = GatewayClient(self)

    @classmethod
    def from_cli(cls, args):
        inst = cls(args.token)
        inst.set_shard(args.shard_id, args.shard_count)
        return inst

    def set_shard(self, shard_number, shard_count):
        self.sharding = {
            'number': shard_number,
            'total': shard_count,
        }

    def run(self):
        return gevent.spawn(self.gw.run)

    def run_forever(self):
        return self.gw.run()
