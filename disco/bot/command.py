import re

from disco.bot.parser import parse_arguments, ArgumentError
from disco.util.cache import cached_property

REGEX_FMT = '({})'
ARGS_REGEX = '( (.*)$|$)'


class CommandEvent(object):
    def __init__(self, command, msg, match):
        self.command = command
        self.msg = msg
        self.match = match
        self.name = self.match.group(1)
        self.args = self.match.group(2).strip().split(' ')

    @cached_property
    def member(self):
        return self.guild.get_member(self.actor)

    @property
    def channel(self):
        return self.msg.channel

    @property
    def guild(self):
        return self.msg.guild

    @property
    def actor(self):
        return self.msg.author


class CommandError(Exception):
    pass


class Command(object):
    def __init__(self, plugin, func, trigger, args=None, aliases=None, group=None, is_regex=False):
        self.plugin = plugin
        self.func = func
        self.triggers = [trigger] + (aliases or [])

        self.args = parse_arguments(args or '')
        self.group = group
        self.is_regex = is_regex

    def execute(self, event):
        if len(event.args) < self.args.required_length:
            raise CommandError('{} requires {} arguments (passed {})'.format(
                event.name,
                self.args.required_length,
                len(event.args)
            ))

        try:
            args = self.args.parse(event.args)
        except ArgumentError as e:
            raise CommandError(e.message)

        return self.func(event, *args)

    @cached_property
    def compiled_regex(self):
        return re.compile(self.regex)

    @property
    def regex(self):
        if self.is_regex:
            return REGEX_FMT.format('|'.join(self.triggers))
        else:
            group = self.group + ' ' if self.group else ''
            return REGEX_FMT.format('|'.join(['^' + group + trigger for trigger in self.triggers]) + ARGS_REGEX)
