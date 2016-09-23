import re

PARTS_RE = re.compile('(\<|\[)((?:\w+|\:|\||\.\.\.| (?:[0-9]+))+)(?:\>|\])')

TYPE_MAP = {
    'str': str,
    'int': int,
    'float': float,
    'snowflake': int,
}


class ArgumentError(Exception):
    pass


class Argument(object):
    def __init__(self, raw):
        self.name = None
        self.count = 1
        self.required = False
        self.types = None
        self.parse(raw)

    @property
    def true_count(self):
        return self.count or 1

    def convert(self, obj):
        for typ in self.types:
            typ = TYPE_MAP.get(typ)
            try:
                return typ(obj)
            except Exception as e:
                continue
        raise e

    def parse(self, raw):
        prefix, part = raw

        if prefix == '<':
            self.required = True
        else:
            self.required = False

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
    def __init__(self, args=None):
        self.args = args or []

    def append(self, arg):
        if self.args and not self.args[-1].required and arg.required:
            raise Exception('Required argument cannot come after an optional argument')

        if self.args and not self.args[-1].count:
            raise Exception('No arguments can come after a catch-all')

        self.args.append(arg)

    def parse(self, rawargs):
        parsed = []

        for index, arg in enumerate(self.args):
            if not arg.required and index + arg.true_count <= len(rawargs):
                continue

            raw = rawargs[index:index + arg.true_count]

            if arg.types:
                for idx, r in enumerate(raw):
                    try:
                        raw[idx] = arg.convert(r)
                    except:
                        raise ArgumentError('cannot convert `{}` to `{}`'.format(
                            r, ', '.join(arg.types)
                        ))

            parsed.append(raw)

        return parsed

    @property
    def length(self):
        return len(self.args)

    @property
    def required_length(self):
        return sum([i.true_count for i in self.args if i.required])


def parse_arguments(line):
    args = ArgumentSet()

    data = PARTS_RE.findall(line)
    if len(data):
        for item in data:
            args.append(Argument(item))

    return args
