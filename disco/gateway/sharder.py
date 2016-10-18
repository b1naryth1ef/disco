import gipc

from disco.client import Client
from disco.bot import Bot, BotConfig
from disco.api.client import APIClient
from disco.gateway.ipc.gipc import GIPCObject, GIPCProxy


def run_shard(config, id, pipe):
    config.shard_id = id
    client = Client(config)
    bot = Bot(client, BotConfig(config.bot))
    GIPCObject(bot, pipe)
    bot.run_forever()


class AutoSharder(object):
    def __init__(self, config):
        self.config = config
        self.client = APIClient(config.token)
        self.shards = {}
        self.config.shard_count = self.client.gateway_bot_get()['shards']

    def run(self):
        for shard in range(self.shard_count):
            self.start_shard(shard)

    def start_shard(self, id):
        cpipe, ppipe = gipc.pipe(duplex=True)
        gipc.start_process(run_shard, (self.config, id, cpipe))
        self.shards[id] = GIPCProxy(ppipe)
