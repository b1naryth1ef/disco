import six
import gevent
import inspect
import weakref
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

    # TODO: dont smash class methods
    @staticmethod
    def add_meta_deco(meta):
        def deco(f):
            if not hasattr(f, 'meta'):
                f.meta = []

            f.meta.append(meta)

            return f
        return deco

    @classmethod
    def with_config(cls, config_cls):
        """
        Sets the plugins config class to the specified config class.
        """
        def deco(plugin_cls):
            plugin_cls.config_cls = config_cls
            return plugin_cls
        return deco

    @classmethod
    def listen(cls, event_name, priority=None):
        """
        Binds the function to listen for a given event name
        """
        return cls.add_meta_deco({
            'type': 'listener',
            'what': 'event',
            'desc': event_name,
            'priority': priority
        })

    @classmethod
    def listen_packet(cls, op, priority=None):
        """
        Binds the function to listen for a given gateway op code
        """
        return cls.add_meta_deco({
            'type': 'listener',
            'what': 'packet',
            'desc': op,
            'priority': priority,
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

    @classmethod
    def schedule(cls, *args, **kwargs):
        """
        Runs a function repeatedly, waiting for a specified interval
        """
        return cls.add_meta_deco({
            'type': 'schedule',
            'args': args,
            'kwargs': kwargs,
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
        self.ctx = bot.ctx
        self.storage = bot.storage
        self.config = config

    @property
    def name(self):
        return self.__class__.__name__

    def bind_all(self):
        self.listeners = []
        self.commands = {}
        self.schedules = {}
        self.greenlets = weakref.WeakSet()

        self._pre = {'command': [], 'listener': []}
        self._post = {'command': [], 'listener': []}

        # TODO: when handling events/commands we need to track the greenlet in
        #  the greenlets set so we can termiante long running commands/listeners
        #  on reload.

        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, 'meta'):
                for meta in member.meta:
                    if meta['type'] == 'listener':
                        self.register_listener(member, meta['what'], meta['desc'], meta['priority'])
                    elif meta['type'] == 'command':
                        meta['kwargs']['update'] = True
                        self.register_command(member, *meta['args'], **meta['kwargs'])
                    elif meta['type'] == 'schedule':
                        self.register_schedule(member, *meta['args'], **meta['kwargs'])
                    elif meta['type'].startswith('pre_') or meta['type'].startswith('post_'):
                        when, typ = meta['type'].split('_', 1)
                        self.register_trigger(typ, when, member)

    def spawn(self, method, *args, **kwargs):
        obj = gevent.spawn(method, *args, **kwargs)
        self.greenlets.add(obj)
        return obj

    def execute(self, event):
        """
        Executes a CommandEvent this plugin owns
        """
        try:
            return event.command.execute(event)
        except CommandError as e:
            event.msg.reply(e.message)
            return False
        finally:
            self.ctx.drop()

    def register_trigger(self, typ, when, func):
        """
        Registers a trigger
        """
        getattr(self, '_' + when)[typ].append(func)

    def _dispatch(self, typ, func, event, *args, **kwargs):
        self.ctx['plugin'] = self

        if hasattr(event, 'guild'):
            self.ctx['guild'] = event.guild
        if hasattr(event, 'channel'):
            self.ctx['channel'] = event.channel
        if hasattr(event, 'author'):
            self.ctx['user'] = event.author

        for pre in self._pre[typ]:
            event = pre(event, args, kwargs)

        if event is None:
            return False

        result = func(event, *args, **kwargs)

        for post in self._post[typ]:
            post(event, args, kwargs, result)

        return True

    def register_listener(self, func, what, desc, priority):
        """
        Registers a listener

        Parameters
        ----------
        what : str
            What the listener is for (event, packet)
        func : function
            The function to be registered.
        desc
            The descriptor of the event/packet.
        priority : Priority
            The priority of this listener.
        """
        func = functools.partial(self._dispatch, 'listener', func)

        priority = priority or Priority.NONE

        if what == 'event':
            li = self.bot.client.events.on(desc, func, priority=priority)
        elif what == 'packet':
            li = self.bot.client.packets.on(desc, func, priority=priority)
        else:
            raise Exception('Invalid listener what: {}'.format(what))

        self.listeners.append(li)

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
        if kwargs.pop('update', False) and func.__name__ in self.commands:
            self.commands[func.__name__].update(*args, **kwargs)
        else:
            wrapped = functools.partial(self._dispatch, 'command', func)
            self.commands[func.__name__] = Command(self, wrapped, *args, **kwargs)

    def register_schedule(self, func, interval, repeat=True, init=True):
        """
        Registers a function to be called repeatedly, waiting for an interval
        duration.

        Args
        ----
        func : function
            The function to be registered.
        interval : int
            Interval (in seconds) to repeat the function on.
        """
        def repeat():
            if init:
                func()

            while True:
                gevent.sleep(interval)
                func()
                if not repeat:
                    break

        self.schedules[func.__name__] = self.spawn(repeat)

    def load(self):
        """
        Called when the plugin is loaded
        """
        self.bind_all()

    def unload(self):
        """
        Called when the plugin is unloaded
        """
        for greenlet in self.greenlets:
            greenlet.kill()

        for listener in self.listeners:
            listener.remove()

        for schedule in six.itervalues(self.schedules):
            schedule.kill()

    def reload(self):
        self.bot.reload_plugin(self.__class__)
