import inspect

from disco.bot.command import Command


class PluginDeco(object):
    @staticmethod
    def listen(event_name):
        def deco(f):
            if not hasattr(f, 'meta'):
                f.meta = []

            f.meta.append({
                'type': 'listener',
                'event_name': event_name,
            })

            return f
        return deco

    @staticmethod
    def command(*args, **kwargs):
        def deco(f):
            if not hasattr(f, 'meta'):
                f.meta = []

            f.meta.append({
                'type': 'command',
                'args': args,
                'kwargs': kwargs,
                })

            return f
        return deco


class Plugin(PluginDeco):
    def __init__(self, bot):
        self.bot = bot

        self.listeners = []
        self.commands = []

        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, 'meta'):
                for meta in member.meta:
                    if meta['type'] == 'listener':
                        self.register_listener(member, meta['event_name'])
                    elif meta['type'] == 'command':
                        self.register_command(member, *meta['args'], **meta['kwargs'])

    def register_listener(self, func, name):
        self.listeners.append(self.bot.client.events.on(name, func))

    def register_command(self, func, *args, **kwargs):
        self.commands.append(Command(func, *args, **kwargs))

    def destroy(self):
        map(lambda k: k.remove(), self._events)

    def load(self):
        pass

    def unload(self):
        pass
