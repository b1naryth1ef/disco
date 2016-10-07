from gevent.lock import RLock


def cached_property(f):
    """
    Creates a cached property out of ``f``. When the property is resolved for
    the first time, the function will be called and its result will be cached.
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
    f._value = None
    f._has_value = False

    def getf(*args, **kwargs):
        if not f._has_value:
            with lock:
                if f._has_value:
                    return f._value

                f._value = f(*args, **kwargs)
                f._has_value = True

        return f._value

    def setf(self, value):
        f._value = value

    def delf(self):
        f._value = None
        f._has_value = False

    return property(getf, setf, delf)
