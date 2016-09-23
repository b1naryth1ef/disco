import re

from disco.client import DiscoClient
from disco.bot.command import CommandEvent


class BotConfig(object):
    # Authentication token
    token = None

    # Whether to enable command parsing
    commands_enabled = True

    # Whether the bot must be mentioned to respond to a command
    command_require_mention = True

    # Rules about what mentions trigger the bot
    command_mention_rules = {
        # 'here': False,
        'everyone': False,
        'role': True,
        'user': True,
    }

    # The prefix required for EVERY command
    command_prefix = ''

    # Whether an edited message can trigger a command
    command_allow_edit = True

    # Function that when given a plugin name, returns its configuration
    plugin_config_provider = None


class Bot(object):
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

    @property
    def commands(self):
        for plugin in self.plugins.values():
            for command in plugin.commands:
                yield command

    def compute_command_matches_re(self):
        re_str = '|'.join(command.regex for command in self.commands)
        if re_str:
            self.command_matches_re = re.compile(re_str)
        else:
            self.command_matches_re = None

    def get_commands_for_message(self, msg):
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
            msg = self.last_message_cache.get(event.message.channel_id)
            if msg and event.message.id == msg[0].id:
                triggered = msg[1]

                if not triggered:
                    triggered = self.handle_message(event.message)

                self.last_message_cache[event.message.channel_id] = (event.message, triggered)

    def add_plugin(self, cls):
        if cls.__name__ in self.plugins:
            raise Exception('Cannot add already added plugin: {}'.format(cls.__name__))

        config = self.config.plugin_config_provider(cls.__name__) if self.config.plugin_config_provider else {}

        self.plugins[cls.__name__] = cls(self, config)
        self.plugins[cls.__name__].load()
        self.compute_command_matches_re()

    def rmv_plugin(self, cls):
        if cls.__name__ not in self.plugins:
            raise Exception('Cannot remove non-existant plugin: {}'.format(cls.__name__))

        self.plugins[cls.__name__].unload()
        self.plugins[cls.__name__].destroy()
        del self.plugins[cls.__name__]
        self.compute_command_matches_re()

    def run_forever(self):
        self.client.run_forever()
