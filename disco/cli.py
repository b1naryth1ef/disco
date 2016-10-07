"""
The CLI module is a small utility that can be used as an easy entry point for
creating and running bots/clients.
"""
from __future__ import print_function

import logging
import argparse

from gevent import monkey

monkey.patch_all()

parser = argparse.ArgumentParser()
parser.add_argument('--token', help='Bot Authentication Token', required=True)
parser.add_argument('--shard-count', help='Total number of shards', default=1)
parser.add_argument('--shard-id', help='Current shard number/id', default=0)
parser.add_argument('--manhole', action='store_true', help='Enable the manhole', default=False)
parser.add_argument('--manhole-bind', help='host:port for the manhole to bind too', default='localhost:8484')
parser.add_argument('--encoder', help='encoder for gateway data', default='json')

logging.basicConfig(level=logging.INFO)


def disco_main():
    """
    Creates an argument parser and parses a standard set of command line arguments,
    creating a new :class:`Client`.

    Returns
    -------
    :class:`Client`
        A new Client from the provided command line arguments
    """
    args = parser.parse_args()

    from disco.client import Client, ClientConfig
    from disco.gateway.encoding import ENCODERS
    from disco.util.token import is_valid_token

    if not is_valid_token(args.token):
        print('Invalid token passed')
        return

    cfg = ClientConfig()
    cfg.token = args.token
    cfg.shard_id = args.shard_id
    cfg.shard_count = args.shard_count
    cfg.manhole_enable = args.manhole
    cfg.manhole_bind = args.manhole_bind
    cfg.encoding_cls = ENCODERS[args.encoder]

    return Client(cfg)

if __name__ == '__main__':
    disco_main().run_forever()
