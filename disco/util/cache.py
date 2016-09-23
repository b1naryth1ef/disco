

def cached_property(f):
    def deco(self, *args, **kwargs):
        if not hasattr(self, '__' + f.__name__):
            setattr(self, '__' + f.__name__, f(self, *args, **kwargs))
        return getattr(self, '__' + f.__name__)
    return property(deco)
