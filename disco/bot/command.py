import re

from disco.util.cache import cached_property

ARGS_REGEX = '( (.*)$|$)'


class CommandEvent(object):
    def __init__(self, msg, match):
        self.msg = msg
        self.match = match
        self.args = self.match.group(1).split(' ')


class Command(object):
    def __init__(self, func, trigger, aliases=None, group=None, is_regex=False):
        self.func = func
        self.triggers = [trigger] + (aliases or [])

        self.group = group
        self.is_regex = is_regex

    def execute(self, msg, match):
        self.func(CommandEvent(msg, match))

    @cached_property
    def compiled_regex(self):
        return re.compile(self.regex)

    @property
    def regex(self):
        if self.is_regex:
            return '|'.join(self.triggers)
        else:
            group = self.group + ' ' if self.group else ''
            return '|'.join(['^' + group + trigger for trigger in self.triggers]) + ARGS_REGEX
