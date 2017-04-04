from __future__ import absolute_import

import gipc
import gevent
import pickle
import logging
import marshal

from six.moves import range

from disco.client import Client
from disco.bot import Bot, BotConfig
from disco.api.client import APIClient
from disco.gateway.ipc import GIPCProxy
from disco.util.logging import setup_logging
from disco.util.snowflake import calculate_shard
from disco.util.serializer import dump_function, load_function


def run_shard(config, shard_id, pipe):
    setup_logging(
        level=logging.INFO,
        format='{} [%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s'.format(shard_id)
    )

    config.shard_id = shard_id
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
        for sid in range(self.count):
            yield sid

    def on(self, id, func):
        if id == self.bot.client.config.shard_id:
            result = gevent.event.AsyncResult()
            result.set(func(self.bot))
            return result

        return self.bot.sharder.call(('run_on', ), id, dump_function(func))

    def all(self, func, timeout=None):
        pool = gevent.pool.Pool(self.count)
        return dict(zip(range(self.count), pool.imap(lambda i: self.on(i, func).wait(timeout=timeout), range(self.count))))

    def for_id(self, sid, func):
        shard = calculate_shard(self.count, sid)
        return self.on(shard, func)


class AutoSharder(object):
    def __init__(self, config):
        self.config = config
        self.client = APIClient(config.token)
        self.shards = {}
        self.config.shard_count = self.client.gateway_bot_get()['shards']

    def run_on(self, sid, raw):
        func = load_function(raw)
        return self.shards[sid].execute(func).wait(timeout=15)

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

    @staticmethod
    def dumps(data):
        if isinstance(data, (basestring, int, long, bool, list, set, dict)):
            return '\x01' + marshal.dumps(data)
        elif isinstance(data, object) and data.__class__.__name__ == 'code':
            return '\x01' + marshal.dumps(data)
        else:
            return '\x02' + pickle.dumps(data)

    @staticmethod
    def loads(data):
        enc_type = data[0]
        if enc_type == '\x01':
            return marshal.loads(data[1:])
        elif enc_type == '\x02':
            return pickle.loads(data[1:])

    def start_shard(self, sid):
        cpipe, ppipe = gipc.pipe(duplex=True, encoder=self.dumps, decoder=self.loads)
        gipc.start_process(run_shard, (self.config, sid, cpipe))
        self.shards[sid] = GIPCProxy(self, ppipe)
