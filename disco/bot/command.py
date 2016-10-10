import re

from holster.enum import Enum

from disco.bot.parser import ArgumentSet, ArgumentError
from disco.util.functional import cached_property

REGEX_FMT = '({})'
ARGS_REGEX = '( (.*)$|$)'
MENTION_RE = re.compile('<@!?([0-9]+)>')

CommandLevels = Enum(
    DEFAULT=0,
    TRUSTED=10,
    MOD=50,
    ADMIN=100,
    OWNER=500,
)


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
        self.name = self.match.group(1)
        self.args = [i for i in self.match.group(2).strip().split(' ') if i]

    @cached_property
    def member(self):
        """
        Guild member (if relevant) for the user that created the message
        """
        return self.guild.get_member(self.author)

    @property
    def channel(self):
        """
        Channel the message was created in
        """
        return self.msg.channel

    @property
    def guild(self):
        """
        Guild (if relevant) the message was created in
        """
        return self.msg.guild

    @property
    def author(self):
        """
        Author of the message
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
        self.update(*args, **kwargs)

    def update(self, args=None, level=None, aliases=None, group=None, is_regex=None):
        self.triggers += aliases or []

        def resolve_role(ctx, id):
            return ctx.msg.guild.roles.get(id)

        def resolve_user(ctx, id):
            return ctx.msg.mentions.get(id)

        self.args = ArgumentSet.from_string(args or '', {
            'mention': self.mention_type([resolve_role, resolve_user]),
            'user': self.mention_type([resolve_user], force=True),
            'role': self.mention_type([resolve_role], force=True),
        })

        self.level = level
        self.group = group
        self.is_regex = is_regex

    @staticmethod
    def mention_type(getters, force=False):
        def _f(ctx, i):
            res = MENTION_RE.match(i)
            if not res:
                raise TypeError('Invalid mention: {}'.format(i))

            id = int(res.group(1))

            for getter in getters:
                obj = getter(ctx, id)
                if obj:
                    return obj

            if force:
                raise TypeError('Cannot resolve mention: {}'.format(id))

            return id
        return _f

    @cached_property
    def compiled_regex(self):
        """
        A compiled version of this command's regex
        """
        return re.compile(self.regex)

    @property
    def regex(self):
        """
        The regex string that defines/triggers this command
        """
        if self.is_regex:
            return REGEX_FMT.format('|'.join(self.triggers))
        else:
            group = ''
            if self.group:
                if self.group in self.plugin.bot.group_abbrev:
                    group = '{}(?:\w+)? '.format(self.plugin.bot.group_abbrev.get(self.group))
                else:
                    group = self.group + ' '
            return REGEX_FMT.format('|'.join(['^' + group + trigger for trigger in self.triggers]) + ARGS_REGEX)

    def execute(self, event):
        """
        Handles the execution of this command given a :class:`CommandEvent`
        object.

        Returns
        -------
        bool
            Whether this command was successful
        """
        if len(event.args) < self.args.required_length:
            raise CommandError('{} requires {} arguments (passed {})'.format(
                event.name,
                self.args.required_length,
                len(event.args)
            ))

        try:
            args = self.args.parse(event.args, ctx=event)
        except ArgumentError as e:
            raise CommandError(e.message)

        return self.func(event, *args)
