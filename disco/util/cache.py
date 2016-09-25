

def cached_property(f):
    def getf(self, *args, **kwargs):
        if not hasattr(self, '__' + f.__name__):
            setattr(self, '__' + f.__name__, f(self, *args, **kwargs))
        return getattr(self, '__' + f.__name__)

    def setf(self, value):
        setattr(self, '__' + f.__name__, value)

    def delf(self):
        setattr(self, '__' + f.__name__, None)

    return property(getf, setf, delf)
