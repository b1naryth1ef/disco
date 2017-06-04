import re
import argparse

from holster.enum import Enum

from disco.bot.parser import ArgumentSet, ArgumentError
from disco.util.functional import cached_property

ARGS_REGEX = '(?: ((?:\n|.)*)$|$)'
ARGS_UNGROUPED_REGEX = '(?: (?:\n|.)*$|$)'
SPLIT_SPACES_NO_QUOTE = re.compile(r'["|\']([^"\']+)["|\']|(\S+)')

USER_MENTION_RE = re.compile('<@!?([0-9]+)>')
ROLE_MENTION_RE = re.compile('<@&([0-9]+)>')
CHANNEL_MENTION_RE = re.compile('<#([0-9]+)>')

CommandLevels = Enum(
    DEFAULT=0,
    TRUSTED=10,
    MOD=50,
    ADMIN=100,
    OWNER=500,
)


class PluginArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandError(message)


class CommandEvent(object):
    """
    An event which is created when a command is triggered. Contains information
    about the message, command, and parsed arguments (along with shortcuts to
    message information).

    Attributes
    ---------
    command : :class:`Command`
        The command this event was created for (aka the triggered command).
    msg : :class:`disco.types.message.Message`
        The message object which triggered this command.
    match : :class:`re.MatchObject`
        The regex match object for the command.
    name : str
        The command name (or alias) which was triggered by the command
    args : list(str)
        Arguments passed to the command
    """

    def __init__(self, command, msg, match):
        self.command = command
        self.msg = msg
        self.match = match
        self.name = self.match.group(1).strip()
        self.args = []

        if self.match.group(2):
            self.args = [i for i in self.match.group(2).strip().split(' ') if i]

    @property
    def codeblock(self):
        if '`' not in self.msg.content:
            return ' '.join(self.args)

        _, src = self.msg.content.split('`', 1)
        src = '`' + src

        if src.startswith('```') and src.endswith('```'):
            src = src[3:-3]
        elif src.startswith('`') and src.endswith('`'):
            src = src[1:-1]

        return src

    @cached_property
    def member(self):
        """
        Guild member (if relevant) for the user that created the message.
        """
        return self.guild.get_member(self.author)

    @property
    def channel(self):
        """
        Channel the message was created in.
        """
        return self.msg.channel

    @property
    def guild(self):
        """
        Guild (if relevant) the message was created in.
        """
        return self.msg.guild

    @property
    def author(self):
        """
        Author of the message.
        """
        return self.msg.author


class CommandError(Exception):
    """
    An exception which is thrown when the arguments for a command are invalid,
    or don't match the command's specifications.
    """


class Command(object):
    """
    An object which defines and handles the triggering of a function based on
    user input (aka a command).

    Attributes
    ----------
    plugin : :class:`disco.bot.plugin.Plugin`
        The plugin this command is a member of.
    func : function
        The function which is called when this command is triggered.
    trigger : str
        The primary trigger (aka name).
    args : Optional[str]
        The argument format specification.
    aliases : Optional[list(str)]
        List of trigger aliases.
    group : Optional[str]
        The group this command is a member of.
    is_regex : Optional[bool]
        Whether the triggers for this command should be treated as raw regex.
    """
    def __init__(self, plugin, func, trigger, *args, **kwargs):
        self.plugin = plugin
        self.func = func
        self.triggers = [trigger]

        self.dispatch_func = None
        self.raw_args = None
        self.args = None
        self.level = None
        self.group = None
        self.is_regex = None
        self.oob = False
        self.context = {}
        self.metadata = {}
        self.parser = None

        self.update(*args, **kwargs)

    @property
    def name(self):
        return self.triggers[0]

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def get_docstring(self):
        return (self.func.__doc__ or '').format(**self.context)

    def update(self, args=None, level=None, aliases=None, group=None, is_regex=None, oob=False, context=None, parser=False, **kwargs):
        self.triggers += aliases or []

        def resolve_role(ctx, rid):
            return ctx.msg.guild.roles.get(rid)

        def resolve_user(ctx, uid):
            if isinstance(uid, int):
                if uid in ctx.msg.mentions:
                    return ctx.msg.mentions.get(uid)
                else:
                    return ctx.msg.client.state.users.get(uid)
            else:
                return ctx.msg.client.state.users.select_one(username=uid[0], discriminator=uid[1])

        def resolve_channel(ctx, cid):
            if isinstance(cid, (int, long)):
                return ctx.msg.guild.channels.get(cid)
            else:
                return ctx.msg.guild.channels.select_one(name=cid)

        def resolve_guild(ctx, gid):
            return ctx.msg.client.state.guilds.get(gid)

        if args:
            self.raw_args = args
            self.args = ArgumentSet.from_string(args, {
                'user': self.mention_type([resolve_user], USER_MENTION_RE, user=True),
                'role': self.mention_type([resolve_role], ROLE_MENTION_RE),
                'channel': self.mention_type([resolve_channel], CHANNEL_MENTION_RE, allow_plain=True),
                'guild': self.mention_type([resolve_guild]),
            })

        self.level = level
        self.group = group
        self.is_regex = is_regex
        self.oob = oob
        self.context = context or {}
        self.metadata = kwargs

        if parser:
            self.parser = PluginArgumentParser(prog=self.name, add_help=False)

    @staticmethod
    def mention_type(getters, reg=None, user=False, allow_plain=False):
        def _f(ctx, raw):
            if raw.isdigit():
                resolved = int(raw)
            elif user and raw.count('#') == 1 and raw.split('#')[-1].isdigit():
                username, discrim = raw.split('#')
                resolved = (username, int(discrim))
            elif reg:
                res = reg.match(raw)
                if res:
                    resolved = int(res.group(1))
                else:
                    if allow_plain:
                        resolved = raw
                    else:
                        raise TypeError('Invalid mention: {}'.format(raw))
            else:
                raise TypeError('Invalid mention: {}'.format(raw))

            for getter in getters:
                obj = getter(ctx, resolved)
                if obj:
                    return obj

            raise TypeError('Cannot resolve mention: {}'.format(raw))
        return _f

    @cached_property
    def compiled_regex(self):
        """
        A compiled version of this command's regex.
        """
        return re.compile(self.regex(), re.I)

    def regex(self, grouped=True):
        """
        The regex string that defines/triggers this command.
        """
        if self.is_regex:
            return '|'.join(self.triggers)
        else:
            group = ''
            if self.group:
                if self.group in self.plugin.bot.group_abbrev:
                    rest = self.plugin.bot.group_abbrev[self.group]
                    group = '{}(?:{}) '.format(rest, ''.join(c + u'?' for c in self.group[len(rest):]))
                else:
                    group = self.group + ' '
            return ('^{}({})' if grouped else '^{}(?:{})').format(
                group,
                '|'.join(self.triggers)
            ) + (ARGS_REGEX if grouped else ARGS_UNGROUPED_REGEX)

    def execute(self, event):
        """
        Handles the execution of this command given a :class:`CommandEvent`
        object.

        Returns
        -------
        bool
            Whether this command was successful
        """
        parsed_kwargs = {}

        if self.args:
            if len(event.args) < self.args.required_length:
                raise CommandError(u'Command {} requires {} arguments (`{}`) passed {}'.format(
                    event.name,
                    self.args.required_length,
                    self.raw_args,
                    len(event.args)
                ))

            try:
                parsed_kwargs = self.args.parse(event.args, ctx=event)
            except ArgumentError as e:
                raise CommandError(e.message)
        elif self.parser:
            event.parser = self.parser
            parsed_kwargs['args'] = self.parser.parse_args(
                [i[0] or i[1] for i in SPLIT_SPACES_NO_QUOTE.findall(' '.join(event.args))])

        kwargs = {}
        kwargs.update(self.context)
        kwargs.update(parsed_kwargs)
        return self.plugin.dispatch('command', self, event, **kwargs)
