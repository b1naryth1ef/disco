from .providers import load_provider


class Storage(object):
    def __init__(self, ctx, config):
        self.ctx = ctx
        self.config = config
        self.provider = load_provider(config.provider)(config.config)
        self.provider.load()
        self.root = self.provider.root()

    @property
    def plugin(self):
        return self.root.ensure('plugins').ensure(self.ctx['plugin'].name)

    @property
    def guild(self):
        return self.plugin.ensure('guilds').ensure(self.ctx['guild'].id)

    @property
    def channel(self):
        return self.plugin.ensure('channels').ensure(self.ctx['channel'].id)

    @property
    def user(self):
        return self.plugin.ensure('users').ensure(self.ctx['user'].id)
