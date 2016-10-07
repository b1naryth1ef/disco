import inspect
import functools

from holster.emitter import Priority

from disco.util.logging import LoggingClass
from disco.bot.command import Command, CommandError


class PluginDeco(object):
    """
    A utility mixin which provides various function decorators that a plugin
    author can use to create bound event/command handlers.
    """
    Prio = Priority

    @staticmethod
    def add_meta_deco(meta):
        def deco(f):
            if not hasattr(f, 'meta'):
                f.meta = []

            f.meta.append(meta)

            return f
        return deco

    @classmethod
    def listen(cls, event_name, priority=None):
        """
        Binds the function to listen for a given event name
        """
        return cls.add_meta_deco({
            'type': 'listener',
            'event_name': event_name,
            'priority': priority
        })

    @classmethod
    def command(cls, *args, **kwargs):
        """
        Creates a new command attached to the function
        """
        return cls.add_meta_deco({
            'type': 'command',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    def pre_command(cls):
        """
        Runs a function before a command is triggered
        """
        return cls.add_meta_deco({
            'type': 'pre_command',
        })

    @classmethod
    def post_command(cls):
        """
        Runs a function after a command is triggered
        """
        return cls.add_meta_deco({
            'type': 'post_command',
        })

    @classmethod
    def pre_listener(cls):
        """
        Runs a function before a listener is triggered
        """
        return cls.add_meta_deco({
            'type': 'pre_listener',
        })

    @classmethod
    def post_listener(cls):
        """
        Runs a function after a listener is triggered
        """
        return cls.add_meta_deco({
            'type': 'post_listener',
        })


class Plugin(LoggingClass, PluginDeco):
    """
    A plugin is a set of listeners/commands which can be loaded/unloaded by a bot.

    Parameters
    ----------
    bot : :class:`disco.bot.Bot`
        The bot this plugin is a member of.
    config : any
        The configuration data for this plugin.

    Attributes
    ----------
    client : :class:`disco.client.Client`
        An alias to the client the bot is running with.
    state : :class:`disco.state.State`
        An alias to the state object for the client.
    listeners : list
        List of all bound listeners this plugin owns.
    commands : list(:class:`disco.bot.command.Command`)
        List of all commands this plugin owns.
    """
    def __init__(self, bot, config):
        super(Plugin, self).__init__()
        self.bot = bot
        self.client = bot.client
        self.state = bot.client.state
        self.config = config

        self.listeners = []
        self.commands = {}

        self._pre = {'command': [], 'listener': []}
        self._post = {'command': [], 'listener': []}

        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, 'meta'):
                for meta in member.meta:
                    if meta['type'] == 'listener':
                        self.register_listener(member, meta['event_name'], meta['priority'])
                    elif meta['type'] == 'command':
                        self.register_command(member, *meta['args'], **meta['kwargs'])
                    elif meta['type'].startswith('pre_') or meta['type'].startswith('post_'):
                        when, typ = meta['type'].split('_', 1)
                        self.register_trigger(typ, when, member)

    def execute(self, event):
        """
        Executes a CommandEvent this plugin owns
        """
        try:
            return event.command.execute(event)
        except CommandError as e:
            event.msg.reply(e.message)
            return False

    def register_trigger(self, typ, when, func):
        """
        Registers a trigger
        """
        getattr(self, '_' + when)[typ].append(func)

    def _dispatch(self, typ, func, event, *args, **kwargs):
        for pre in self._pre[typ]:
            event = pre(event, args, kwargs)

        if event is None:
            return False

        result = func(event, *args, **kwargs)

        for post in self._post[typ]:
            post(event, args, kwargs, result)

        return True

    def register_listener(self, func, name, priority):
        """
        Registers a listener

        Parameters
        ----------
        func : function
            The function to be registered.
        name : string
            Name of event to listen for.
        priority : Priority
            The priority of this listener.
        """
        func = functools.partial(self._dispatch, 'listener', func)
        self.listeners.append(self.bot.client.events.on(name, func, priority=priority or Priority.NONE))

    def register_command(self, func, *args, **kwargs):
        """
        Registers a command

        Parameters
        ----------
        func : function
            The function to be registered.
        args
            Arguments to pass onto the :class:`disco.bot.command.Command` object.
        kwargs
            Keyword arguments to pass onto the :class:`disco.bot.command.Command`
            object.
        """
        wrapped = functools.partial(self._dispatch, 'command', func)
        self.commands[func.__name__] = Command(self, wrapped, *args, **kwargs)

    def destroy(self):
        """
        Destroys the plugin (removing all listeners)
        """
        map(lambda k: k.remove(), self._events)

    def load(self):
        """
        Called when the plugin is loaded
        """
        pass

    def unload(self):
        """
        Called when the plugin is unloaded
        """
        pass
