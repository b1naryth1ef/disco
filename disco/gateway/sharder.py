from __future__ import absolute_import

import gipc
import gevent
import logging
import dill

from holster.log import set_logging_levels

from disco.client import Client
from disco.bot import Bot, BotConfig
from disco.api.client import APIClient
from disco.gateway.ipc.gipc import GIPCProxy


def run_on(id, proxy):
    def f(func):
        return proxy.call(('run_on', ), id, dill.dumps(func))
    return f


def run_self(bot):
    def f(func):
        result = gevent.event.AsyncResult()
        result.set(func(bot))
        return result
    return f


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
    bot.shards = {
        i: run_on(i, bot.sharder) for i in range(config.shard_count)
        if i != id
    }
    bot.shards[id] = run_self(bot)
    bot.run_forever()


class AutoSharder(object):
    def __init__(self, config):
        self.config = config
        self.client = APIClient(config.token)
        self.shards = {}
        self.config.shard_count = self.client.gateway_bot_get()['shards']
        if self.config.shard_count > 1:
            self.config.shard_count = 10

    def run_on(self, id, raw):
        func = dill.loads(raw)
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
        cpipe, ppipe = gipc.pipe(duplex=True, encoder=dill.dumps, decoder=dill.loads)
        gipc.start_process(run_shard, (self.config, id, cpipe))
        self.shards[id] = GIPCProxy(self, ppipe)
