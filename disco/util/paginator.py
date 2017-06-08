import operator


class Paginator(object):
    """
    Implements a class which provides paginated iteration over an endpoint.
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

        self._key = kwargs.pop('key', operator.attrgetter('id'))
        self._bulk = kwargs.pop('bulk', False)
        self._after = kwargs.pop('after', None)
        self._buffer = []

    def fill(self):
        self.kwargs['after'] = self._after
        result = self.func(*self.args, **self.kwargs)

        if not len(result):
            return

        self._buffer.extend(result)
        self._after = self._key(result[-1])

    def next(self):
        return self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        if not len(self._buffer):
            self.fill()

        if self._bulk:
            res = self._buffer
            self._buffer = []
            return res
        else:
            return self._buffer.pop()
