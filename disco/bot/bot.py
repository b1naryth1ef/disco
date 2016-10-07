import re

from disco.bot.command import CommandEvent


class BotConfig(object):
    """
    An object which is used to configure and define the runtime configuration for
    a bot.

    Attributes
    ----------
    token : str
        The authentication token for this bot. This is passed on to the
        :class:`disco.client.Client` without any validation.
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
    plugin_config_provider : Optional[function]
        If set, this function will be called before loading a plugin, with the
        plugins name. Its expected to return a type of configuration object the
        plugin understands.
    """
    token = None

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

    plugin_config_provider = None


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

        if self.client.config.manhole_enable:
            self.client.manhole_locals['bot'] = self

        self.plugins = {}

        # Only bind event listeners if we're going to parse commands
        if self.config.commands_enabled:
            self.client.events.on('MessageCreate', self.on_message_create)

            if self.config.commands_allow_edit:
                self.client.events.on('MessageUpdate', self.on_message_update)

        # Stores the last message for every single channel
        self.last_message_cache = {}

        # Stores a giant regex matcher for all commands
        self.command_matches_re = None

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
        for plugin in self.plugins.values():
            for command in plugin.commands.values():
                yield command

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
            match = any((
                self.config.commands_mention_rules['user'] and msg.is_mentioned(self.client.state.me),
                self.config.commands_mention_rules['everyone'] and msg.mention_everyone,
                self.config.commands_mention_rules['role'] and any(map(msg.is_mentioned,
                    msg.guild.get_member(self.client.state.me).roles
                ))))

            if not match:
                raise StopIteration

            content = msg.without_mentions.strip()

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
            return any([
                command.plugin.execute(CommandEvent(command, msg, match))
                for command, match in commands
            ])

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

    def add_plugin(self, cls):
        """
        Adds and loads a plugin, based on its class.

        Parameters
        ----------
        cls : subclass of :class:`disco.bot.plugin.Plugin`
            Plugin class to initialize and load.
        """
        if cls.__name__ in self.plugins:
            raise Exception('Cannot add already added plugin: {}'.format(cls.__name__))

        config = self.config.plugin_config_provider(cls.__name__) if self.config.plugin_config_provider else None

        self.plugins[cls.__name__] = cls(self, config)
        self.plugins[cls.__name__].load()
        self.compute_command_matches_re()

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
        self.plugins[cls.__name__].destroy()
        del self.plugins[cls.__name__]
        self.compute_command_matches_re()

    def run_forever(self):
        """
        Runs this bots core loop forever
        """
        self.client.run_forever()
