import re
import os
import six
import inspect
import importlib

from six.moves import reload_module
from holster.threadlocal import ThreadLocal

from disco.types.guild import GuildMember
from disco.bot.plugin import Plugin
from disco.bot.command import CommandEvent, CommandLevels
from disco.bot.storage import Storage
from disco.util.config import Config
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
    """
    levels = {}
    plugins = []

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
    plugin_config_format = 'yaml'
    plugin_config_dir = 'config'

    storage_enabled = True
    storage_provider = 'memory'
    storage_config = {}


class Bot(object):
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

        # The context carries information about events in a threadlocal storage
        self.ctx = ThreadLocal()

        # The storage object acts as a dynamic contextual aware store
        self.storage = None
        if self.config.storage_enabled:
            self.storage = Storage(self.ctx, self.config.from_prefix('storage'))

        if self.client.config.manhole_enable:
            self.client.manhole_locals['bot'] = self

        self.plugins = {}
        self.group_abbrev = {}

        # Only bind event listeners if we're going to parse commands
        if self.config.commands_enabled:
            self.client.events.on('MessageCreate', self.on_message_create)

            if self.config.commands_allow_edit:
                self.client.events.on('MessageUpdate', self.on_message_update)

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
        Generator of all commands this bots plugins have defined
        """
        for plugin in six.itervalues(self.plugins):
            for command in six.itervalues(plugin.commands):
                yield command

    def recompute(self):
        """
        Called when a plugin is loaded/unloaded to recompute internal state.
        """
        if self.config.commands_group_abbrev:
            self.compute_group_abbrev()

        self.compute_command_matches_re()

    def compute_group_abbrev(self):
        """
        Computes all possible abbreviations for a command grouping
        """
        self.group_abbrev = {}
        groups = set(command.group for command in self.commands if command.group)

        for group in groups:
            grp = group
            while grp:
                # If the group already exists, means someone else thought they
                #  could use it so we need to
                if grp in list(six.itervalues(self.group_abbrev)):
                    self.group_abbrev = {k: v for k, v in six.iteritems(self.group_abbrev) if v != grp}
                else:
                    self.group_abbrev[group] = grp

                grp = grp[:-1]

    def compute_command_matches_re(self):
        """
        Computes a single regex which matches all possible command combinations.
        """
        re_str = '|'.join(command.regex for command in self.commands)
        if re_str:
            self.command_matches_re = re.compile(re_str)
        else:
            self.command_matches_re = None

    def get_commands_for_message(self, msg):
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

        if self.config.commands_require_mention:
            mention_direct = msg.is_mentioned(self.client.state.me)
            mention_everyone = msg.mention_everyone

            mention_roles = []
            if msg.guild:
                mention_roles = list(filter(lambda r: msg.is_mentioned(r),
                    msg.guild.get_member(self.client.state.me).roles))

            if not any((
                self.config.commands_mention_rules['user'] and mention_direct,
                self.config.commands_mention_rules['everyone'] and mention_everyone,
                self.config.commands_mention_rules['role'] and any(mention_roles),
                msg.channel.is_dm
            )):
                raise StopIteration

            if mention_direct:
                if msg.guild:
                    member = msg.guild.get_member(self.client.state.me)
                    if member:
                        content = content.replace(member.mention, '', 1)
                else:
                    content = content.replace(self.client.state.me.mention, '', 1)
            elif mention_everyone:
                content = content.replace('@everyone', '', 1)
            else:
                for role in mention_roles:
                    content = content.replace(role.mention, '', 1)

            content = content.lstrip()

        if self.config.commands_prefix and not content.startswith(self.config.commands_prefix):
            raise StopIteration
        else:
            content = content[len(self.config.commands_prefix):]

        if not self.command_matches_re or not self.command_matches_re.match(content):
            raise StopIteration

        for command in self.commands:
            match = command.compiled_regex.match(content)
            if match:
                yield (command, match)

    def get_level(self, actor):
        level = CommandLevels.DEFAULT

        if callable(self.config.commands_level_getter):
            level = self.config.commands_level_getter(actor)
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
        commands = list(self.get_commands_for_message(msg))

        if len(commands):
            result = False
            for command, match in commands:
                if not self.check_command_permissions(command, msg):
                    continue

                if command.plugin.execute(CommandEvent(command, msg, match)):
                    result = True
            return result

        return False

    def on_message_create(self, event):
        if event.message.author.id == self.client.state.me.id:
            return

        if self.config.commands_allow_edit:
            self.last_message_cache[event.message.channel_id] = (event.message, False)

        self.handle_message(event.message)

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

    def add_plugin(self, cls, config=None):
        """
        Adds and loads a plugin, based on its class.

        Parameters
        ----------
        cls : subclass of :class:`disco.bot.plugin.Plugin`
            Plugin class to initialize and load.
        config : Optional
            The configuration to load the plugin with.
        """
        if cls.__name__ in self.plugins:
            raise Exception('Cannot add already added plugin: {}'.format(cls.__name__))

        if not config:
            if callable(self.config.plugin_config_provider):
                config = self.config.plugin_config_provider(cls)
            else:
                config = self.load_plugin_config(cls)

        self.plugins[cls.__name__] = cls(self, config)
        self.plugins[cls.__name__].load()
        self.recompute()

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

        self.plugins[cls.__name__].unload()
        del self.plugins[cls.__name__]
        self.recompute()

    def reload_plugin(self, cls):
        """
        Reloads a plugin.
        """
        config = self.plugins[cls.__name__].config

        self.rmv_plugin(cls)
        module = reload_module(inspect.getmodule(cls))
        self.add_plugin(getattr(module, cls.__name__), config)

    def run_forever(self):
        """
        Runs this bots core loop forever
        """
        self.client.run_forever()

    def add_plugin_module(self, path, config=None):
        """
        Adds and loads a plugin, based on its module path.
        """

        mod = importlib.import_module(path)
        loaded = False

        for entry in map(lambda i: getattr(mod, i), dir(mod)):
            if inspect.isclass(entry) and issubclass(entry, Plugin) and not entry == Plugin:
                loaded = True
                self.add_plugin(entry, config)

        if not loaded:
            raise Exception('Could not find any plugins to load within module {}'.format(path))

    def load_plugin_config(self, cls):
        name = cls.__name__.lower()
        if name.startswith('plugin'):
            name = name[6:]

        path = os.path.join(
            self.config.plugin_config_dir, name) + '.' + self.config.plugin_config_format

        if not os.path.exists(path):
            if hasattr(cls, 'config_cls'):
                return cls.config_cls()
            return

        with open(path, 'r') as f:
            data = Serializer.loads(self.config.plugin_config_format, f.read())

        if hasattr(cls, 'config_cls'):
            inst = cls.config_cls()
            inst.update(data)
            return inst

        return data
