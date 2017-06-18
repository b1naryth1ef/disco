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
parser.add_argument('--config', help='Configuration file', default='config.json')
parser.add_argument('--token', help='Bot Authentication Token', default=None)
parser.add_argument('--shard-count', help='Total number of shards', default=None)
parser.add_argument('--shard-id', help='Current shard number/id', default=None)
parser.add_argument('--shard-auto', help='Automatically run all shards', action='store_true', default=False)
parser.add_argument('--manhole', action='store_true', help='Enable the manhole', default=None)
parser.add_argument('--manhole-bind', help='host:port for the manhole to bind too', default=None)
parser.add_argument('--encoder', help='encoder for gateway data', default=None)
parser.add_argument('--run-bot', help='run a disco bot on this client', action='store_true', default=False)
parser.add_argument('--plugin', help='load plugins into the bot', nargs='*', default=[])
parser.add_argument('--log-level', help='log level', default='info')
parser.add_argument('--http-bind', help='bind information for http server', default=None)


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
    from disco.util.logging import setup_logging

    if os.path.exists(args.config):
        config = ClientConfig.from_file(args.config)
    else:
        config = ClientConfig()

    config.manhole_enable = args.manhole
    config.manhole_bind = args.manhole_bind.split(':', 1)

    for k, v in six.iteritems(vars(args)):
        if hasattr(config, k) and v is not None:
            setattr(config, k, v)

    if not is_valid_token(config.token):
        print('Invalid token passed')
        return

    if args.shard_auto:
        from disco.gateway.sharder import AutoSharder
        AutoSharder(config).run()
        return

    # TODO: make configurable
    setup_logging(level=getattr(logging, args.log_level.upper()))

    client = Client(config)

    bot = None
    if args.run_bot or hasattr(config, 'bot'):
        bot_config = BotConfig(config.bot) if hasattr(config, 'bot') else BotConfig()
        if not hasattr(bot_config, 'plugins'):
            bot_config.plugins = args.plugin
        else:
            bot_config.plugins += args.plugin

        if args.http_bind:
            bot_config.http_enabled = True
            host, port = args.http_bind.split(':', 1)
            bot_config.http_host = host
            bot_config.http_port = int(port)

        bot = Bot(client, bot_config)

    if run:
        (bot or client).run_forever()

    return (bot or client)

if __name__ == '__main__':
    disco_main(True)
