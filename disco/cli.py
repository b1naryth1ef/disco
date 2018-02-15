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

# Command line specific arguments
parser.add_argument('--run-bot', help='run a disco bot on this client', action='store_true', default=False)
parser.add_argument('--plugin', help='load plugins into the bot', nargs='*', default=[])
parser.add_argument('--config', help='Configuration file', default=None)
parser.add_argument('--shard-auto', help='Automatically run all shards', action='store_true', default=False)

# Configuration overrides
parser.add_argument('--token', help='Bot Authentication Token', default=None)
parser.add_argument('--shard-id', help='Current shard number/id', default=None)
parser.add_argument('--shard-count', help='Total number of shards', default=None)
parser.add_argument('--max-reconnects', help='Maximum reconnect attempts', default=None)
parser.add_argument('--log-level', help='log level', default=None)
parser.add_argument('--manhole', action='store_true', help='Enable the manhole', default=None)
parser.add_argument('--manhole-bind', help='host:port for the manhole to bind too', default=None)
parser.add_argument('--encoder', help='encoder for gateway data', default=None)


# Mapping of argument names to configuration overrides
CONFIG_OVERRIDE_MAPPING = {
    'token': 'token',
    'shard_id': 'shard_id',
    'shard_count': 'shard_count',
    'max_reconnects': 'max_reconnects',
    'log_level': 'log_level',
    'manhole': 'manhole_enable',
    'manhole_bind': 'manhole_bind',
    'encoder': 'encoder',
}


def disco_main(run=False):
    """
    Creates an argument parser and parses a standard set of command line arguments,
    creating a new :class:`Client`.

    Returns
    -------
    :class:`Client`
        A new Client from the provided command line arguments
    """
    from disco.client import Client, ClientConfig
    from disco.bot import Bot, BotConfig
    from disco.util.logging import setup_logging

    # Parse out all our command line arguments
    args = parser.parse_args()

    # Create the base configuration object
    if args.config:
        config = ClientConfig.from_file(args.config)
    else:
        if os.path.exists('config.json'):
            config = ClientConfig.from_file('config.json')
        elif os.path.exists('config.yaml'):
            config = ClientConfig.from_file('config.yaml')
        else:
            config = ClientConfig()

    for arg_key, config_key in six.iteritems(CONFIG_OVERRIDE_MAPPING):
        if getattr(args, arg_key) is not None:
            setattr(config, config_key, getattr(args, arg_key))

    # Setup the auto-sharder
    if args.shard_auto:
        from disco.gateway.sharder import AutoSharder
        AutoSharder(config).run()
        return

    # Setup logging based on the configured level
    setup_logging(level=getattr(logging, config.log_level.upper()))

    # Build out client object
    client = Client(config)

    # If applicable, build the bot and load plugins
    bot = None
    if args.run_bot or hasattr(config, 'bot'):
        bot_config = BotConfig(config.bot) if hasattr(config, 'bot') else BotConfig()
        if not hasattr(bot_config, 'plugins'):
            bot_config.plugins = args.plugin
        else:
            bot_config.plugins += args.plugin

        bot = Bot(client, bot_config)

    if run:
        (bot or client).run_forever()

    return (bot or client)


if __name__ == '__main__':
    disco_main(True)
