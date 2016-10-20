from __future__ import absolute_import

import gipc
import gevent
import logging
import marshal

from holster.log import set_logging_levels

from disco.client import Client
from disco.bot import Bot, BotConfig
from disco.api.client import APIClient
from disco.gateway.ipc import GIPCProxy
from disco.util.snowflake import calculate_shard
from disco.util.serializer import dump_function, load_function


def run_shard(config, id, pipe):
    logging.basicConfig(
        level=logging.INFO,
        format='{} [%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s'.format(id)
    )
    set_logging_levels()

    config.shard_id = id
    client = Client(config)
    bot = Bot(client, BotConfig(config.bot))
    bot.sharder = GIPCProxy(bot, pipe)
    bot.shards = ShardHelper(config.shard_count, bot)
    bot.run_forever()


class ShardHelper(object):
    def __init__(self, count, bot):
        self.count = count
        self.bot = bot

    def keys(self):
        for id in xrange(self.count):
            yield id

    def on(self, id, func):
        if id == self.bot.client.config.shard_id:
            result = gevent.event.AsyncResult()
            result.set(func(self.bot))
            return result

        return self.bot.sharder.call(('run_on', ), id, dump_function(func))

    def all(self, func, timeout=None):
        pool = gevent.pool.Pool(self.count)
        return dict(zip(range(self.count), pool.imap(lambda i: self.on(i, func).wait(timeout=timeout), range(self.count))))

    def for_id(self, id, func):
        shard = calculate_shard(self.count, id)
        return self.on(shard, func)


class AutoSharder(object):
    def __init__(self, config):
        self.config = config
        self.client = APIClient(config.token)
        self.shards = {}
        self.config.shard_count = self.client.gateway_bot_get()['shards']
        if self.config.shard_count > 1:
            self.config.shard_count = 10

    def run_on(self, id, raw):
        func = load_function(raw)
        return self.shards[id].execute(func).wait(timeout=15)

    def run(self):
        for shard in range(self.config.shard_count):
            if self.config.manhole_enable and shard != 0:
                self.config.manhole_enable = False

            self.start_shard(shard)
            gevent.sleep(6)

        logging.basicConfig(
            level=logging.INFO,
            format='{} [%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s'.format(id)
        )

    def start_shard(self, id):
        cpipe, ppipe = gipc.pipe(duplex=True, encoder=marshal.dumps, decoder=marshal.loads)
        gipc.start_process(run_shard, (self.config, id, cpipe))
        self.shards[id] = GIPCProxy(self, ppipe)
