import re

from disco.client import DiscoClient
from disco.bot.command import CommandEvent


class BotConfig(object):
    """
    An object which specifies the runtime configuration for a Bot.

    :ivar str token: Authentication token
    :ivar bool commands_enabled: whether to enable the command parsing functionality
        of the bot
    :ivar bool command_require_mention: whether commands require a mention to be
        triggered
    :ivar dict command_mention_rules: a dictionary of rules about what types of
        mentions will trigger a command. A string/bool mapping containing 'here',
        'everyone', 'role', and 'user'. If set to false, the mention type will
        not trigger commands.
    :ivar str command_prefix: prefix required to trigger a command
    :ivar bool command_allow_edit: whether editing the last-sent message in a channel,
        which did not previously trigger a command, will cause the bot to recheck
        the message contents and possibly trigger a command.
    :ivar function plugin_config_provider: an optional function which when called
        with a plugin name, returns relevant configuration for it.
    """
    token = None

    commands_enabled = True
    command_require_mention = True
    command_mention_rules = {
        # 'here': False,
        'everyone': False,
        'role': True,
        'user': True,
    }
    command_prefix = ''
    command_allow_edit = True

    plugin_config_provider = None


class Bot(object):
    """
    Disco's implementation of a simple but extendable Discord bot. Bots consist
    of a set of plugins, and a Disco client.

    :param client: the client this bot should use for its Discord connection
    :param config: a :class:`BotConfig` instance

    :ivar dict plugins: string -> :class:`disco.bot.plugin.Plugin` mapping of
        all loaded plugins
    """
    def __init__(self, client=None, config=None):
        self.client = client or DiscoClient(config.token)
        self.config = config or BotConfig()

        self.plugins = {}

        # Only bind event listeners if we're going to parse commands
        if self.config.commands_enabled:
            self.client.events.on('MessageCreate', self.on_message_create)

            if self.config.command_allow_edit:
                self.client.events.on('MessageUpdate', self.on_message_update)

        # Stores the last message for every single channel
        self.last_message_cache = {}

        # Stores a giant regex matcher for all commands
        self.command_matches_re = None

    @classmethod
    def from_cli(cls, *plugins):
        """
        Creates a new instance of the bot using the Disco-CLI utility, and a set
        of passed-in plugin classes.

        :param plugins: plugins to load after creaing the Bot instance
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
        Generator of all commands a given message triggers.
        """
        content = msg.content

        if self.config.command_require_mention:
            match = any((
                self.config.command_mention_rules['user'] and msg.is_mentioned(self.client.state.me),
                self.config.command_mention_rules['everyone'] and msg.mention_everyone,
                self.config.command_mention_rules['role'] and any(map(msg.is_mentioned,
                    msg.guild.get_member(self.client.state.me).roles
                ))))

            if not match:
                raise StopIteration

            content = msg.without_mentions.strip()

        if self.config.command_prefix and not content.startswith(self.config.command_prefix):
            raise StopIteration
        else:
            content = content[len(self.config.command_prefix):]

        if not self.command_matches_re or not self.command_matches_re.match(content):
            raise StopIteration

        for command in self.commands:
            match = command.compiled_regex.match(content)
            if match:
                yield (command, match)

    def handle_message(self, msg):
        """
        Attempts to handle a newely created or edited message in the context of
        command parsing/triggering. Calls all relevant commands the message triggers.

        :returns: whether any commands where successfully triggered
        :rtype: bool
        """
        commands = list(self.get_commands_for_message(msg))

        if len(commands):
            return any([
                command.plugin.execute(CommandEvent(command, msg, match))
                for command, match in commands
            ])

        return False

    def on_message_create(self, event):
        if self.config.command_allow_edit:
            self.last_message_cache[event.message.channel_id] = (event.message, False)

        self.handle_message(event.message)

    def on_message_update(self, event):
        if self.config.command_allow_edit:
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
        Adds and loads a given plugin, based on its class (which must be a subclass
        of :class:`disco.bot.plugin.Plugin`).
        """
        if cls.__name__ in self.plugins:
            raise Exception('Cannot add already added plugin: {}'.format(cls.__name__))

        config = self.config.plugin_config_provider(cls.__name__) if self.config.plugin_config_provider else None

        self.plugins[cls.__name__] = cls(self, config)
        self.plugins[cls.__name__].load()
        self.compute_command_matches_re()

    def rmv_plugin(self, cls):
        """
        Unloads and removes a given plugin, based on its class (which must be a
        sub class of :class:`disco.bot.plugin.Plugin`).
        """
        if cls.__name__ not in self.plugins:
            raise Exception('Cannot remove non-existant plugin: {}'.format(cls.__name__))

        self.plugins[cls.__name__].unload()
        self.plugins[cls.__name__].destroy()
        del self.plugins[cls.__name__]
        self.compute_command_matches_re()

    def run_forever(self):
        """
        Runs this bot forever
        """
        self.client.run_forever()
