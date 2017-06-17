import six
import types
import gevent
import inspect
import weakref
import functools

from gevent.event import AsyncResult
from holster.emitter import Priority

from disco.util.logging import LoggingClass
from disco.bot.command import Command, CommandError


class BasePluginDeco(object):
    Prio = Priority

    # TODO: dont smash class methods
    @classmethod
    def add_meta_deco(cls, meta):
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
    def listen(cls, *args, **kwargs):
        """
        Binds the function to listen for a given event name.
        """
        return cls.add_meta_deco({
            'type': 'listener',
            'what': 'event',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    def listen_packet(cls, *args, **kwargs):
        """
        Binds the function to listen for a given gateway op code.
        """
        return cls.add_meta_deco({
            'type': 'listener',
            'what': 'packet',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    def command(cls, *args, **kwargs):
        """
        Creates a new command attached to the function.
        """

        return cls.add_meta_deco({
            'type': 'command',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    def pre_command(cls):
        """
        Runs a function before a command is triggered.
        """
        return cls.add_meta_deco({
            'type': 'pre_command',
        })

    @classmethod
    def post_command(cls):
        """
        Runs a function after a command is triggered.
        """
        return cls.add_meta_deco({
            'type': 'post_command',
        })

    @classmethod
    def pre_listener(cls):
        """
        Runs a function before a listener is triggered.
        """
        return cls.add_meta_deco({
            'type': 'pre_listener',
        })

    @classmethod
    def post_listener(cls):
        """
        Runs a function after a listener is triggered.
        """
        return cls.add_meta_deco({
            'type': 'post_listener',
        })

    @classmethod
    def schedule(cls, *args, **kwargs):
        """
        Runs a function repeatedly, waiting for a specified interval.
        """
        return cls.add_meta_deco({
            'type': 'schedule',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    def add_argument(cls, *args, **kwargs):
        """
        Adds an argument to the argument parser.
        """
        return cls.add_meta_deco({
            'type': 'parser.add_argument',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    def route(cls, *args, **kwargs):
        """
        Adds an HTTP route.
        """
        return cls.add_meta_deco({
            'type': 'http.add_route',
            'args': args,
            'kwargs': kwargs,
        })


class PluginDeco(BasePluginDeco):
    """
    A utility mixin which provides various function decorators that a plugin
    author can use to create bound event/command handlers.
    """
    parser = BasePluginDeco


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

        # General declartions
        self.listeners = []
        self.commands = []
        self.schedules = {}
        self.greenlets = weakref.WeakSet()
        self._pre = {}
        self._post = {}

        # This is an array of all meta functions we sniff at init
        self.meta_funcs = []

        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, 'meta'):
                self.meta_funcs.append(member)

                # Unsmash local functions
                if hasattr(Plugin, name):
                    method = types.MethodType(getattr(Plugin, name), self, self.__class__)
                    setattr(self, name, method)

        self.bind_all()

    @property
    def name(self):
        return self.__class__.__name__

    def bind_all(self):
        self.listeners = []
        self.commands = []
        self.schedules = {}
        self.greenlets = weakref.WeakSet()

        self._pre = {'command': [], 'listener': []}
        self._post = {'command': [], 'listener': []}

        for member in self.meta_funcs:
            for meta in reversed(member.meta):
                self.bind_meta(member, meta)

    def bind_meta(self, member, meta):
        if meta['type'] == 'listener':
            self.register_listener(member, meta['what'], *meta['args'], **meta['kwargs'])
        elif meta['type'] == 'command':
            # meta['kwargs']['update'] = True
            self.register_command(member, *meta['args'], **meta['kwargs'])
        elif meta['type'] == 'schedule':
            self.register_schedule(member, *meta['args'], **meta['kwargs'])
        elif meta['type'].startswith('pre_') or meta['type'].startswith('post_'):
            when, typ = meta['type'].split('_', 1)
            self.register_trigger(typ, when, member)
        elif meta['type'].startswith('parser.'):
            for command in self.commands:
                if command.func == member:
                    getattr(command.parser, meta['type'].split('.', 1)[-1])(
                        *meta['args'],
                        **meta['kwargs'])
        elif meta['type'] == 'http.add_route':
            meta['kwargs']['view_func'] = member
            self.bot.http.add_url_rule(*meta['args'], **meta['kwargs'])
        else:
            raise Exception('unhandled meta type {}'.format(meta))

    def handle_exception(self, greenlet, event):
        pass

    def wait_for_event(self, event_name, conditional=None, **kwargs):
        result = AsyncResult()
        listener = None

        def _event_callback(event):
            for k, v in kwargs.items():
                obj = event
                for inst in k.split('__'):
                    obj = getattr(obj, inst)

                if obj != v:
                    break
            else:
                if conditional and not conditional(event):
                    return

                listener.remove()
                return result.set(event)

        listener = self.bot.client.events.on(event_name, _event_callback)

        return result

    def spawn_wrap(self, spawner, method, *args, **kwargs):
        def wrapped(*args, **kwargs):
            self.ctx['plugin'] = self
            try:
                res = method(*args, **kwargs)
                return res
            finally:
                self.ctx.drop()

        obj = spawner(wrapped, *args, **kwargs)
        self.greenlets.add(obj)
        return obj

    def spawn(self, *args, **kwargs):
        return self.spawn_wrap(gevent.spawn, *args, **kwargs)

    def spawn_later(self, delay, *args, **kwargs):
        return self.spawn_wrap(functools.partial(gevent.spawn_later, delay), *args, **kwargs)

    def execute(self, event):
        """
        Executes a CommandEvent this plugin owns.
        """
        if not event.command.oob:
            self.greenlets.add(gevent.getcurrent())
        try:
            return event.command.execute(event)
        except CommandError as e:
            event.msg.reply(e.message)
            return False
        finally:
            self.ctx.drop()

    def register_trigger(self, typ, when, func):
        """
        Registers a trigger.
        """
        getattr(self, '_' + when)[typ].append(func)

    def dispatch(self, typ, func, event, *args, **kwargs):
        # Link the greenlet with our exception handler
        gevent.getcurrent().link_exception(lambda g: self.handle_exception(g, event))

        # TODO: this is ugly
        if typ != 'command':
            self.greenlets.add(gevent.getcurrent())

        self.ctx['plugin'] = self

        if hasattr(event, 'guild'):
            self.ctx['guild'] = event.guild
        if hasattr(event, 'channel'):
            self.ctx['channel'] = event.channel
        if hasattr(event, 'author'):
            self.ctx['user'] = event.author

        for pre in self._pre[typ]:
            event = pre(func, event, args, kwargs)

        if event is None:
            return False

        result = func(event, *args, **kwargs)

        for post in self._post[typ]:
            post(func, event, args, kwargs, result)

        return True

    def register_listener(self, func, what, *args, **kwargs):
        """
        Registers a listener.

        Parameters
        ----------
        what : str
            What the listener is for (event, packet)
        func : function
            The function to be registered.
        desc
            The descriptor of the event/packet.
        """
        args = list(args) + [functools.partial(self.dispatch, 'listener', func)]

        if what == 'event':
            li = self.bot.client.events.on(*args, **kwargs)
        elif what == 'packet':
            li = self.bot.client.packets.on(*args, **kwargs)
        else:
            raise Exception('Invalid listener what: {}'.format(what))

        self.listeners.append(li)

    def register_command(self, func, *args, **kwargs):
        """
        Registers a command.

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
        self.commands.append(Command(self, func, *args, **kwargs))

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
        repeat : bool
            Whether this schedule is repeating (or one time).
        init : bool
            Whether to run this schedule once immediatly, or wait for the first
            scheduled iteration.
        """
        def repeat_func():
            if init:
                func()

            while True:
                gevent.sleep(interval)
                func()
                if not repeat:
                    break

        self.schedules[func.__name__] = self.spawn(repeat_func)

    def load(self, ctx):
        """
        Called when the plugin is loaded.
        """
        pass

    def unload(self, ctx):
        """
        Called when the plugin is unloaded.
        """
        for greenlet in self.greenlets:
            greenlet.kill()

        for listener in self.listeners:
            listener.remove()

        for schedule in six.itervalues(self.schedules):
            schedule.kill()

    def reload(self):
        self.bot.reload_plugin(self.__class__)
