from six.moves import range

NO_MORE_SENTINEL = object()


def take(seq, count):
    """
    Take count many elements from a sequence or generator.

    Args
    ----
    seq : sequence or generator
        The sequence to take elements from.
    count : int
        The number of elements to take.
    """
    for _ in range(count):
        i = next(seq, NO_MORE_SENTINEL)
        if i is NO_MORE_SENTINEL:
            return
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


def simple_cached_property(method):
    key = '_{}'.format(method.__name__)

    def _getattr(inst):
        try:
            return getattr(inst, key)
        except AttributeError:
            value = method(inst)
            setattr(inst, key, value)
            return value

    def _setattr(inst, value):
        setattr(inst, key, value)

    def _delattr(inst):
        delattr(inst, key)

    return property(_getattr, _setattr, _delattr)
