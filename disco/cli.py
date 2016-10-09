"""
The CLI module is a small utility that can be used as an easy entry point for
creating and running bots/clients.
"""
from __future__ import print_function

import os
import six
import logging
import argparse

from gevent import monkey

monkey.patch_all()

parser = argparse.ArgumentParser()
parser.add_argument('--config', help='Configuration file', default='config.yaml')
parser.add_argument('--token', help='Bot Authentication Token', default=None)
parser.add_argument('--shard-count', help='Total number of shards', default=None)
parser.add_argument('--shard-id', help='Current shard number/id', default=None)
parser.add_argument('--manhole', action='store_true', help='Enable the manhole', default=None)
parser.add_argument('--manhole-bind', help='host:port for the manhole to bind too', default=None)
parser.add_argument('--encoder', help='encoder for gateway data', default=None)
parser.add_argument('--run-bot', help='run a disco bot on this client', action='store_true', default=False)
parser.add_argument('--plugin', help='load plugins into the bot', nargs='*', default=[])

logging.basicConfig(level=logging.INFO)


def disco_main(run=False):
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
    from disco.bot import Bot, BotConfig
    from disco.util.token import is_valid_token

    if os.path.exists(args.config):
        config = ClientConfig.from_file(args.config)
    else:
        config = ClientConfig()

    for k, v in six.iteritems(vars(args)):
        if hasattr(config, k) and v is not None:
            setattr(config, k, v)

    if not is_valid_token(config.token):
        print('Invalid token passed')
        return

    client = Client(config)

    bot = None
    if args.run_bot or hasattr(config, 'bot'):
        bot_config = BotConfig(config.bot) if hasattr(config, 'bot') else BotConfig()
        bot_config.plugins += args.plugin
        bot = Bot(client, bot_config)

    if run:
        (bot or client).run_forever()

    return (bot or client)

if __name__ == '__main__':
    disco_main(True)
