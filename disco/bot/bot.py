import re


class BotConfig(object):
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


class Bot(object):
    def __init__(self, client, config=None):
        self.client = client
        self.config = config or BotConfig()

        self.plugins = {}

        self.client.events.on('MessageCreate', self.on_message_create)
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
        print re_str
        if re_str:
            self.command_matches_re = re.compile(re_str)
        else:
            self.command_matches_re = None

    def handle_message(self, msg):
        content = msg.content

        if self.config.command_require_mention:
            match = any((
                self.config.command_mention_rules['user'] and msg.is_mentioned(self.client.state.me),
                self.config.command_mention_rules['everyone'] and msg.mention_everyone,
                self.config.command_mention_rules['role'] and any(map(msg.is_mentioned,
                    msg.guild.get_member(self.client.state.me).roles
                ))))

            if not match:
                return False

            content = msg.without_mentions.strip()

        if self.config.command_prefix and not content.startswith(self.config.command_prefix):
            return False

        if not self.command_matches_re or not self.command_matches_re.match(content):
            return False

        for command in self.commands:
            match = command.compiled_regex.match(content)
            if match:
                command.execute(msg, match)

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

        self.plugins[cls.__name__] = cls(self)
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
