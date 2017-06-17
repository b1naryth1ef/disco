import re
import os
import six
import gevent
import inspect
import importlib

from six.moves import reload_module
from holster.threadlocal import ThreadLocal
from gevent.wsgi import WSGIServer

from disco.types.guild import GuildMember
from disco.bot.plugin import Plugin
from disco.bot.command import CommandEvent, CommandLevels
from disco.bot.storage import Storage
from disco.util.config import Config
from disco.util.logging import LoggingClass
from disco.util.serializer import Serializer


class BotConfig(Config):
    """
    An object which is used to configure and define the runtime configuration for
    a bot.

    Attributes
    ----------
    levels : dict(snowflake, str)
        Mapping of user IDs/role IDs to :class:`disco.bot.commands.CommandLevesls`
        which is used for the default commands_level_getter.
    plugins : list[string]
        List of plugin modules to load.
    commands_enabled : bool
        Whether this bot instance should utilize command parsing. Generally this
        should be true, unless your bot is only handling events and has no user
        interaction.
    commands_require_mention : bool
        Whether messages must mention the bot to be considered for command parsing.
    commands_mention_rules : dict(str, bool)
        A dictionary describing what mention types can be considered a mention
        of the bot when using :attr:`commands_require_mention`. This dictionary
        can contain the following keys: `here`, `everyone`, `role`, `user`. When
        a keys value is set to true, the mention type will be considered for
        command parsing.
    commands_prefix : str
        A string prefix that is required for a message to be considered for
        command parsing.
    commands_allow_edit : bool
        If true, the bot will reparse an edited message if it was the last sent
        message in a channel, and did not previously trigger a command. This is
        helpful for allowing edits to typod commands.
    commands_level_getter : function
        If set, a function which when given a GuildMember or User, returns the
        relevant :class:`disco.bot.commands.CommandLevels`.
    commands_group_abbrev : function
        If true, command groups may be abbreviated to the least common variation.
        E.g. the grouping 'test' may be abbreviated down to 't', unless 'tag' exists,
        in which case it may be abbreviated down to 'te'.
    plugin_config_provider : Optional[function]
        If set, this function will replace the default configuration loading
        function, which normally attempts to load a file located at config/plugin_name.fmt
        where fmt is the plugin_config_format. The function here should return
        a valid configuration object which the plugin understands.
    plugin_config_format : str
        The serialization format plugin configuration files are in.
    plugin_config_dir : str
        The directory plugin configuration is located within.
    http_enabled : bool
        Whether to enable the built-in Flask server which allows plugins to handle
        and route HTTP requests.
    http_host : str
        The host string for the HTTP Flask server (if enabled)
    http_port : int
        The port for the HTTP Flask server (if enabled)
    """
    levels = {}
    plugins = []
    plugin_config = {}

    commands_enabled = True
    commands_require_mention = True
    commands_mention_rules = {
        # 'here': False,
        'everyone': False,
        'role': True,
        'user': True,
    }
    commands_prefix = ''
    commands_allow_edit = True
    commands_level_getter = None
    commands_group_abbrev = True

    plugin_config_provider = None
    plugin_config_format = 'json'
    plugin_config_dir = 'config'

    storage_enabled = True
    storage_fsync = True
    storage_serializer = 'json'
    storage_path = 'storage.json'

    http_enabled = False
    http_host = '0.0.0.0'
    http_port = 7575


class Bot(LoggingClass):
    """
    Disco's implementation of a simple but extendable Discord bot. Bots consist
    of a set of plugins, and a Disco client.

    Parameters
    ----------
    client : :class:`disco.client.Client`
        The client this bot should utilize for its connection.
    config : Optional[:class:`BotConfig`]
        The configuration to use for this bot. If not provided will use the defaults
        inside of :class:`BotConfig`.

    Attributes
    ----------
    client : `disco.client.Client`
        The client instance for this bot.
    config : `BotConfig`
        The bot configuration instance for this bot.
    plugins : dict(str, :class:`disco.bot.plugin.Plugin`)
        Any plugins this bot has loaded
    """
    def __init__(self, client, config=None):
        self.client = client
        self.config = config or BotConfig()

        # Shard manager
        self.shards = None

        # The context carries information about events in a threadlocal storage
        self.ctx = ThreadLocal()

        # The storage object acts as a dynamic contextual aware store
        self.storage = None
        if self.config.storage_enabled:
            self.storage = Storage(self.ctx, self.config.from_prefix('storage'))

        # If the manhole is enabled, add this bot as a local
        if self.client.config.manhole_enable:
            self.client.manhole_locals['bot'] = self

        if self.config.http_enabled:
            from flask import Flask
            self.log.info('Starting HTTP server bound to %s:%s', self.config.http_host, self.config.http_port)
            self.http = Flask('disco')
            self.http_server = WSGIServer((self.config.http_host, self.config.http_port), self.http)
            self.http_server_greenlet = gevent.spawn(self.http_server.serve_forever)

        self.plugins = {}
        self.group_abbrev = {}

        # Only bind event listeners if we're going to parse commands
        if self.config.commands_enabled:
            self.client.events.on('MessageCreate', self.on_message_create)

            if self.config.commands_allow_edit:
                self.client.events.on('MessageUpdate', self.on_message_update)

        # If we have a level getter and its a string, try to load it
        if isinstance(self.config.commands_level_getter, six.string_types):
            mod, func = self.config.commands_level_getter.rsplit('.', 1)
            mod = importlib.import_module(mod)
            self.config.commands_level_getter = getattr(mod, func)

        # Stores the last message for every single channel
        self.last_message_cache = {}

        # Stores a giant regex matcher for all commands
        self.command_matches_re = None

        # Finally, load all the plugin modules that where passed with the config
        for plugin_mod in self.config.plugins:
            self.add_plugin_module(plugin_mod)

        # Convert level mapping
        for k, v in six.iteritems(self.config.levels):
            self.config.levels[k] = CommandLevels.get(v)

    @classmethod
    def from_cli(cls, *plugins):
        """
        Creates a new instance of the bot using the utilities inside of the
        :mod:`disco.cli` module. Allows passing in a set of uninitialized
        plugin classes to load.

        Parameters
        ---------
        plugins : Optional[list(:class:`disco.bot.plugin.Plugin`)]
            Any plugins to load after creating the new bot instance

        """
        from disco.cli import disco_main
        inst = cls(disco_main())

        for plugin in plugins:
            inst.add_plugin(plugin)

        return inst

    @property
    def commands(self):
        """
        Generator of all commands this bots plugins have defined.
        """
        for plugin in six.itervalues(self.plugins):
            for command in plugin.commands:
                yield command

    def recompute(self):
        """
        Called when a plugin is loaded/unloaded to recompute internal state.
        """
        if self.config.commands_group_abbrev:
            groups = set(command.group for command in self.commands if command.group)
            self.group_abbrev = self.compute_group_abbrev(groups)

        self.compute_command_matches_re()

    def compute_group_abbrev(self, groups):
        """
        Computes all possible abbreviations for a command grouping.
        """
        # For the first pass, we just want to compute each groups possible
        #  abbreviations that don't conflict with eachother.
        possible = {}
        for group in groups:
            for index in range(1, len(group)):
                current = group[:index]
                if current in possible:
                    possible[current] = None
                else:
                    possible[current] = group

        # Now, we want to compute the actual shortest abbreivation out of the
        #  possible ones
        result = {}
        for abbrev, group in six.iteritems(possible):
            if not group:
                continue

            if group in result:
                if len(abbrev) < len(result[group]):
                    result[group] = abbrev
            else:
                result[group] = abbrev

        return result

    def compute_command_matches_re(self):
        """
        Computes a single regex which matches all possible command combinations.
        """
        commands = list(self.commands)
        re_str = '|'.join(command.regex(grouped=False) for command in commands)
        if re_str:
            self.command_matches_re = re.compile(re_str, re.I)
        else:
            self.command_matches_re = None

    def get_commands_for_message(self, require_mention, mention_rules, prefix, msg):
        """
        Generator of all commands that a given message object triggers, based on
        the bots plugins and configuration.

        Parameters
        ---------
        msg : :class:`disco.types.message.Message`
            The message object to parse and find matching commands for

        Yields
        -------
        tuple(:class:`disco.bot.command.Command`, `re.MatchObject`)
            All commands the message triggers
        """
        content = msg.content

        if require_mention:
            mention_direct = msg.is_mentioned(self.client.state.me)
            mention_everyone = msg.mention_everyone

            mention_roles = []
            if msg.guild:
                mention_roles = list(filter(lambda r: msg.is_mentioned(r),
                                            msg.guild.get_member(self.client.state.me).roles))

            if not any((
                mention_rules.get('user', True) and mention_direct,
                mention_rules.get('everyone', False) and mention_everyone,
                mention_rules.get('role', False) and any(mention_roles),
                msg.channel.is_dm
            )):
                return []

            if mention_direct:
                if msg.guild:
                    member = msg.guild.get_member(self.client.state.me)
                    if member:
                        # If nickname is set, filter both the normal and nick mentions
                        if member.nick:
                            content = content.replace(member.mention, '', 1)
                        content = content.replace(member.user.mention, '', 1)
                else:
                    content = content.replace(self.client.state.me.mention, '', 1)
            elif mention_everyone:
                content = content.replace('@everyone', '', 1)
            else:
                for role in mention_roles:
                    content = content.replace('<@{}>'.format(role), '', 1)

            content = content.lstrip()

        if prefix and not content.startswith(prefix):
            return []
        else:
            content = content[len(prefix):]

        if not self.command_matches_re or not self.command_matches_re.match(content):
            return []

        options = []
        for command in self.commands:
            match = command.compiled_regex.match(content)
            if match:
                options.append((command, match))
        return sorted(options, key=lambda obj: obj[0].group is None)

    def get_level(self, actor):
        level = CommandLevels.DEFAULT

        if callable(self.config.commands_level_getter):
            level = self.config.commands_level_getter(self, actor)
        else:
            if actor.id in self.config.levels:
                level = self.config.levels[actor.id]

            if isinstance(actor, GuildMember):
                for rid in actor.roles:
                    if rid in self.config.levels and self.config.levels[rid] > level:
                        level = self.config.levels[rid]

        return level

    def check_command_permissions(self, command, msg):
        if not command.level:
            return True

        level = self.get_level(msg.author if not msg.guild else msg.guild.get_member(msg.author))

        if level >= command.level:
            return True
        return False

    def handle_message(self, msg):
        """
        Attempts to handle a newly created or edited message in the context of
        command parsing/triggering. Calls all relevant commands the message triggers.

        Parameters
        ---------
        msg : :class:`disco.types.message.Message`
            The newly created or updated message object to parse/handle.

        Returns
        -------
        bool
            whether any commands where successfully triggered by the message
        """
        commands = list(self.get_commands_for_message(
            self.config.commands_require_mention,
            self.config.commands_mention_rules,
            self.config.commands_prefix,
            msg
        ))

        if not len(commands):
            return False

        for command, match in commands:
            if not self.check_command_permissions(command, msg):
                continue

            if command.plugin.execute(CommandEvent(command, msg, match)):
                return True
        return False

    def on_message_create(self, event):
        if event.message.author.id == self.client.state.me.id:
            return

        result = self.handle_message(event.message)

        if self.config.commands_allow_edit:
            self.last_message_cache[event.message.channel_id] = (event.message, result)

    def on_message_update(self, event):
        if self.config.commands_allow_edit:
            obj = self.last_message_cache.get(event.message.channel_id)
            if not obj:
                return

            msg, triggered = obj
            if msg.id == event.message.id and not triggered:
                msg.update(event.message)
                triggered = self.handle_message(msg)

                self.last_message_cache[msg.channel_id] = (msg, triggered)

    def add_plugin(self, inst, config=None, ctx=None):
        """
        Adds and loads a plugin, based on its class.

        Parameters
        ----------
        inst : subclass (or instance therein) of `disco.bot.plugin.Plugin`
            Plugin class to initialize and load.
        config : Optional
            The configuration to load the plugin with.
        ctx : Optional[dict]
            Context (previous state) to pass the plugin. Usually used along w/
            unload.
        """
        if inspect.isclass(inst):
            if not config:
                if callable(self.config.plugin_config_provider):
                    config = self.config.plugin_config_provider(inst)
                else:
                    config = self.load_plugin_config(inst)

            inst = inst(self, config)

        if inst.__class__.__name__ in self.plugins:
            self.log.warning('Attempted to add already added plugin %s', inst.__class__.__name__)
            raise Exception('Cannot add already added plugin: {}'.format(inst.__class__.__name__))

        self.ctx['plugin'] = self.plugins[inst.__class__.__name__] = inst
        self.plugins[inst.__class__.__name__].load(ctx or {})
        self.recompute()
        self.ctx.drop()

    def rmv_plugin(self, cls):
        """
        Unloads and removes a plugin based on its class.

        Parameters
        ----------
        cls : subclass of :class:`disco.bot.plugin.Plugin`
            Plugin class to unload and remove.
        """
        if cls.__name__ not in self.plugins:
            raise Exception('Cannot remove non-existant plugin: {}'.format(cls.__name__))

        ctx = {}
        self.plugins[cls.__name__].unload(ctx)
        del self.plugins[cls.__name__]
        self.recompute()
        return ctx

    def reload_plugin(self, cls):
        """
        Reloads a plugin.
        """
        config = self.plugins[cls.__name__].config

        ctx = self.rmv_plugin(cls)
        module = reload_module(inspect.getmodule(cls))
        self.add_plugin(getattr(module, cls.__name__), config, ctx)

    def run_forever(self):
        """
        Runs this bots core loop forever.
        """
        self.client.run_forever()

    def add_plugin_module(self, path, config=None):
        """
        Adds and loads a plugin, based on its module path.
        """
        self.log.info('Adding plugin module at path "%s"', path)
        mod = importlib.import_module(path)
        loaded = False

        for entry in map(lambda i: getattr(mod, i), dir(mod)):
            if inspect.isclass(entry) and issubclass(entry, Plugin) and not entry == Plugin:
                if getattr(entry, '_shallow', False) and Plugin in entry.__bases__:
                    continue
                loaded = True
                self.add_plugin(entry, config)

        if not loaded:
            raise Exception('Could not find any plugins to load within module {}'.format(path))

    def load_plugin_config(self, cls):
        name = cls.__name__.lower()
        if name.endswith('plugin'):
            name = name[:-6]

        path = os.path.join(
            self.config.plugin_config_dir, name) + '.' + self.config.plugin_config_format

        data = {}
        if name in self.config.plugin_config:
            data.update(self.config.plugin_config[name])

        if os.path.exists(path):
            with open(path, 'r') as f:
                data.update(Serializer.loads(self.config.plugin_config_format, f.read()))

        if hasattr(cls, 'config_cls'):
            inst = cls.config_cls()
            if data:
                inst.update(data)
            return inst

        return data
