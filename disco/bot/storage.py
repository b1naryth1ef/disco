from .backends import BACKENDS


class Storage(object):
    def __init__(self, ctx, config):
        self.ctx = ctx
        self.backend = BACKENDS[config.backend]
        # TODO: autosave
        # config.autosave config.autosave_interval

    @property
    def guild(self):
        return self.backend.base().ensure('guilds').ensure(self.ctx['guild'].id)

    @property
    def channel(self):
        return self.backend.base().ensure('channels').ensure(self.ctx['channel'].id)

    @property
    def user(self):
        return self.backend.base().ensure('users').ensure(self.ctx['user'].id)
