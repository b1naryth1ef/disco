import operator


class Paginator(object):
    """
    Implements a class which provides paginated iteration over an endpoint.
    """
    def __init__(self, func, sort_key, *args, **kwargs):
        self.func = func
        self.sort_key = sort_key
        self.args = args
        self.kwargs = kwargs

        self._key = kwargs.pop('key', operator.attrgetter('id'))
        self._bulk = kwargs.pop('bulk', False)
        self._sort_key_value = kwargs.pop(self.sort_key, None)
        self._buffer = []

    def fill(self):
        self.kwargs[self.sort_key] = self._sort_key_value
        result = self.func(*self.args, **self.kwargs)

        if not len(result):
            return 0

        self._buffer.extend(result)
        self._sort_key_value = self._key(result[-1])
        return len(result)

    def next(self):
        return self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        if not len(self._buffer):
            if not self.fill():
                raise StopIteration

        if self._bulk:
            res = self._buffer
            self._buffer = []
            return res
        else:
            return self._buffer.pop()
