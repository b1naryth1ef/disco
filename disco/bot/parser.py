import re
import copy


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
    def __init__(self, args=None, custom_types=None):
        self.args = args or []
        self.types = copy.copy(TYPE_MAP)
        self.types.update(custom_types)

    def convert(self, types, value):
        for typ_name in types:
            typ = self.types.get(typ_name)
            if not typ:
                raise Exception('Unknown type {}'.format(typ_name))

            try:
                return typ(value)
            except Exception as e:
                continue

        raise e

    def append(self, arg):
        if self.args and not self.args[-1].required and arg.required:
            raise Exception('Required argument cannot come after an optional argument')

        if self.args and not self.args[-1].count:
            raise Exception('No arguments can come after a catch-all')

        self.args.append(arg)

    def parse(self, rawargs):
        parsed = []

        for index, arg in enumerate(self.args):
            if not arg.required and index + arg.true_count > len(rawargs):
                continue

            if arg.count == 0:
                raw = rawargs[index:]
            else:
                raw = rawargs[index:index + arg.true_count]

            if arg.types:
                for idx, r in enumerate(raw):
                    try:
                        raw[idx] = self.convert(arg.types, r)
                    except:
                        raise ArgumentError('cannot convert `{}` to `{}`'.format(
                            r, ', '.join(arg.types)
                        ))

            if arg.count == 1:
                raw = raw[0]

            if (not arg.types or arg.types == ['str']) and isinstance(raw, list):
                raw = ' '.join(raw)

            parsed.append(raw)

        return parsed

    @property
    def length(self):
        return len(self.args)

    @property
    def required_length(self):
        return sum([i.true_count for i in self.args if i.required])


def parse_arguments(line, custom_types=None):
    args = ArgumentSet(custom_types=custom_types)

    data = PARTS_RE.findall(line)
    if len(data):
        for item in data:
            args.append(Argument(item))

    return args
