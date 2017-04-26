import gevent

"""
Object.chain -> creates a chain where each action happens after the last
    pass_result = False -> whether the result of the last action is passed, or the original

Object.async_chain -> creates an async chain where each action happens at the same time
"""


class Chainable(object):
    __slots__ = []

    def chain(self, pass_result=True):
        return Chain(self, pass_result=pass_result, async_=False)

    def async_chain(self):
        return Chain(self, pass_result=False, async_=True)


class Chain(object):
    def __init__(self, obj, pass_result=True, async_=False):
        self._obj = obj
        self._pass_result = pass_result
        self._async = async_
        self._parts = []

    @property
    def obj(self):
        if isinstance(self._obj, Chain):
            return self._obj._next()
        return self._obj

    def __getattr__(self, item):
        func = getattr(self.obj, item)
        if not func or not callable(func):
            return func

        def _wrapped(*args, **kwargs):
            inst = gevent.spawn(func, *args, **kwargs)
            self._parts.append(inst)

            # If async, just return instantly
            if self._async:
                return self

            # Otherwise return a chain
            return Chain(self)
        return _wrapped

    def _next(self):
        res = self._parts[0].get()
        if self._pass_result:
            return res
        return self

    def then(self, func, *args, **kwargs):
        inst = gevent.spawn(func, *args, **kwargs)
        self._parts.append(inst)
        if self._async:
            return self
        return Chain(self)

    def first(self):
        return self._obj

    def get(self, timeout=None):
        return gevent.wait(self._parts, timeout=timeout)

    def wait(self, timeout=None):
        gevent.joinall(self._parts, timeout=None)
