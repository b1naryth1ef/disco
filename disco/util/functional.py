from six.moves import range

NO_MORE_SENTINEL = object()


def take(seq, count):
    """
    Take count many elements from a sequence or generator.

    Args
    ----
    seq : sequnce or generator
        The sequnce to take elements from.
    count : int
        The number of elments to take.
    """
    for _ in range(count):
        i = next(seq, NO_MORE_SENTINEL)
        if i is NO_MORE_SENTINEL:
            raise StopIteration
        yield i


def chunks(obj, size):
    """
    Splits a list into sized chunks.

    Args
    ----
    obj : list
        List to split up.
    size : int
        Size of chunks to split list into.
    """
    for i in range(0, len(obj), size):
        yield obj[i:i + size]


def one_or_many(f):
    """
    Wraps a function so that it will either take a single argument, or a variable
    number of args.
    """
    def _f(*args):
        if len(args) == 1:
            return f(args[0])
        return f(*args)
    return _f


class CachedSlotProperty(object):
    __slots__ = ['stored_name', 'function', '__doc__']

    def __init__(self, name, function):
        self.stored_name = '_' + name
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    def __get__(self, instance, owner):
        if instance is None:
            return self

        try:
            return getattr(instance, self.stored_name)
        except AttributeError:
            value = self.function(instance)
            setattr(instance, self.stored_name, value)
            return value


def cached_property(f):
    return CachedSlotProperty(f.__name__, f)
