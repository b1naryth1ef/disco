from gevent.lock import RLock


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
