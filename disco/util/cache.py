

def cached_property(f):
    def deco(self, *args, **kwargs):
        self.__dict__[f.__name__] = f(self, *args, **kwargs)
        return self.__dict__[f.__name__]
    return property(deco)
