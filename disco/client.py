import logging
import gevent

from holster.emitter import Emitter

from disco.state import State
from disco.api.client import APIClient
from disco.gateway.client import GatewayClient

log = logging.getLogger(__name__)


class DiscoClient(object):
    """
    The DiscoClient represents the base entry point to utilizing the Discord API
    through disco. It wraps the functionality of both the REST API, and the realtime
    secure websocket gateway.

    Parameters
    ----------
    token : str
        The Discord authentication token which is used for both the :class:`APIClient`
        and the :class:`GatewayClient`. This token can be validated before being
        passed in, by using the :func:`disco.util.token.is_valid_token` function.
    sharding : Optional[dict(str, int)]
        A dictionary containing two pairs with information that is used to control
        the sharding behavior of the :class:`GatewayClient`. By setting the `number`
        key, the current shard ID can be controlled. While when setting the `total`
        key, the total number of running shards can be set.

    Attributes
    ----------
    events : :class:`Emitter`
        An emitter which emits Gateway events
    packets : :class:`Emitter`
        An emitter which emits Gateway packets
    state : :class:`State`
        The state tracking object
    api : :class:`APIClient`
        The API client
    gw : :class:`GatewayClient`
        The gateway client
    """
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
        """
        Create a new client from a argparse command line argument object, usually
        generated from the :func:`disco_main` function.
        """
        inst = cls(
            token=args.token,
            sharding={
                'number': args.shard_id,
                'total': args.shard_count,
            })
        return inst

    def run(self):
        """
        Run the client (e.g. the :class:`GatewayClient`) in a new greenlet
        """
        return gevent.spawn(self.gw.run)

    def run_forever(self):
        """
        Run the client (e.g. the :class:`GatewayClient`) in the current greenlet
        """
        return self.gw.run()
