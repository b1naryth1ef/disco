import six
import unicodedata

from disco.types.message import Sendable


class MessageTable(Sendable):
    def __init__(self, sep=' | ', codeblock=True, header_break=True, language=None):
        self.header = []
        self.entries = []
        self.size_index = {}
        self.sep = sep
        self.codeblock = codeblock
        self.header_break = header_break
        self.language = language

    def recalculate_size_index(self, cols):
        for idx, col in enumerate(cols):
            size = len(unicodedata.normalize('NFC', col))
            if idx not in self.size_index or size > self.size_index[idx]:
                self.size_index[idx] = size

    def set_header(self, *args):
        args = list(map(six.text_type, args))
        self.header = args
        self.recalculate_size_index(args)

    def add(self, *args):
        args = list(map(six.text_type, args))
        self.entries.append(args)
        self.recalculate_size_index(args)

    def compile_one(self, cols):
        data = self.sep.lstrip()

        for idx, col in enumerate(cols):
            padding = ' ' * (self.size_index[idx] - len(col))
            data += col + padding + self.sep

        return data.rstrip()

    def compile(self):
        data = []
        if self.header:
            data = [self.compile_one(self.header)]

        if self.header and self.header_break:
            data.append('-' * (sum(self.size_index.values()) + (len(self.header) * len(self.sep)) + 1))

        for row in self.entries:
            data.append(self.compile_one(row))

        if self.codeblock:
            return self.fit((self.lanague if self.language else '') + '\n'.join(data))

        # TODO: truncate by line
        return self.truncate('\n'.join(data), tail='')
