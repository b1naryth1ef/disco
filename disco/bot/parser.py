import re
import six
import copy

# Regex which splits out argument parts
PARTS_RE = re.compile('(\<|\[|\{)((?:\w+|\:|\||\.\.\.| (?:[0-9]+))+)(?:\>|\]|\})')

BOOL_OPTS = {'yes': True, 'no': False, 'true': True, 'False': False, '1': True, '0': False}

# Mapping of types
TYPE_MAP = {
    'str': lambda ctx, data: str(data) if six.PY3 else unicode(data),
    'int': lambda ctx, data: int(data),
    'float': lambda ctx, data: int(data),
    'snowflake': lambda ctx, data: int(data),
}


def to_bool(ctx, data):
    if data in BOOL_OPTS:
        return BOOL_OPTS[data]
    raise TypeError

TYPE_MAP['bool'] = to_bool


class ArgumentError(Exception):
    """
    An error thrown when passed in arguments cannot be conformed/casted to the
    argument specification.
    """


class Argument(object):
    """
    A single argument, which is normally the member of a :class:`ArgumentSet`.

    Attributes
    ----------
    name : str
        The name of this argument.
    count : int
        The number of raw arguments that compose this argument.
    required : bool
        Whether this is a required argument.
    types : list(type)
        Types this argument supports.
    """
    def __init__(self, raw):
        self.name = None
        self.count = 1
        self.required = False
        self.flag = False
        self.types = None
        self.parse(raw)

    @property
    def true_count(self):
        """
        The true number of raw arguments this argument takes.
        """
        return self.count or 1

    def parse(self, raw):
        """
        Attempts to parse arguments from their raw form.
        """
        prefix, part = raw

        if prefix == '<':
            self.required = True
        else:
            self.required = False

        # Whether this is a flag
        self.flag = (prefix == '{')

        if not self.flag:
            if part.endswith('...'):
                part = part[:-3]
                self.count = 0
            elif ' ' in part:
                split = part.split(' ', 1)
                part, self.count = split[0], int(split[1])

            if ':' in part:
                part, typeinfo = part.split(':')
                self.types = typeinfo.split('|')

        self.name = part.strip()


class ArgumentSet(object):
    """
    A set of :class:`Argument` instances which forms a larger argument specification.

    Attributes
    ----------
    args : list(:class:`Argument`)
        All arguments that are a member of this set.
    types : dict(str, type)
        All types supported by this ArgumentSet.
    """
    def __init__(self, args=None, custom_types=None):
        self.args = args or []
        self.types = copy.copy(TYPE_MAP)
        self.types.update(custom_types or {})

    @classmethod
    def from_string(cls, line, custom_types=None):
        """
        Creates a new :class:`ArgumentSet` from a given argument string specification.
        """
        args = cls(custom_types=custom_types)

        data = PARTS_RE.findall(line)
        if len(data):
            for item in data:
                args.append(Argument(item))

        return args

    def convert(self, ctx, types, value):
        """
        Attempts to convert a value to one or more types.

        Parameters
        ----------
        types : list(type)
            List of types to attempt conversion with.
        value : str
            The string value to attempt conversion on.
        """
        for typ_name in types:
            typ = self.types.get(typ_name)
            if not typ:
                raise Exception('Unknown type {}'.format(typ_name))

            try:
                return typ(ctx, value)
            except Exception as e:
                continue

        raise e

    def append(self, arg):
        """
        Add a new :class:`Argument` to this argument specification/set.
        """
        if self.args and not self.args[-1].required and arg.required:
            raise Exception('Required argument cannot come after an optional argument')

        if self.args and not self.args[-1].count:
            raise Exception('No arguments can come after a catch-all')

        self.args.append(arg)

    def parse(self, rawargs, ctx=None):
        """
        Parse a string of raw arguments into this argument specification.
        """
        parsed = {}

        flags = {i.name: i for i in self.args if i.flag}
        if flags:
            new_rawargs = []

            for offset, raw in enumerate(rawargs):
                if raw.startswith('-'):
                    raw = raw.lstrip('-')
                    if raw in flags:
                        parsed[raw] = True
                        continue
                new_rawargs.append(raw)

            rawargs = new_rawargs

        for index, arg in enumerate((arg for arg in self.args if not arg.flag)):
            if not arg.required and index + arg.true_count > len(rawargs):
                continue

            if arg.count == 0:
                raw = rawargs[index:]
            else:
                raw = rawargs[index:index + arg.true_count]

            if arg.types:
                for idx, r in enumerate(raw):
                    try:
                        raw[idx] = self.convert(ctx, arg.types, r)
                    except:
                        raise ArgumentError(u'cannot convert `{}` to `{}`'.format(
                            r, ', '.join(arg.types)
                        ))

            if arg.count == 1:
                raw = raw[0]

            if (not arg.types or arg.types == ['str']) and isinstance(raw, list):
                raw = ' '.join(raw)

            parsed[arg.name] = raw

        return parsed

    @property
    def length(self):
        """
        The number of arguments in this set/specification.
        """
        return len(self.args)

    @property
    def required_length(self):
        """
        The number of required arguments to compile this set/specificaiton.
        """
        return sum([i.true_count for i in self.args if i.required])
