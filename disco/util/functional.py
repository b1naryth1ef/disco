from gevent.lock import RLock

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


def cached_property(f):
    """
    Creates a cached class property out of ``f``. When the property is resolved
    for the first time, the function will be called and its result will be cached.
    Subsequent calls will return the cached value. If this property is set, the
    cached value will be replaced (or set initially) with the value provided. If
    this property is deleted, the cache will be cleared and the next call will
    refill it with a new value.

    Notes
    -----
    This function is greenlet safe.

    Args
    ----
    f : function
        The function to wrap.

    Returns
    -------
    property
        The cached property created.
    """
    lock = RLock()
    value_name = '_' + f.__name__

    def getf(self, *args, **kwargs):
        if not hasattr(self, value_name):
            with lock:
                if hasattr(self, value_name):
                    return getattr(self, value_name)

                setattr(self, value_name, f(self, *args, **kwargs))

        return getattr(self, value_name)

    def setf(self, value):
        setattr(self, value_name, value)

    def delf(self):
        delattr(self, value_name)

    return property(getf, setf, delf)
