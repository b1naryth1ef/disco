

class Serializer(object):
    FORMATS = {
        'json',
        'yaml',
        'pickle',
    }

    @classmethod
    def check_format(cls, fmt):
        if fmt not in cls.FORMATS:
            raise Exception('Unsupported serilization format: {}'.format(fmt))

    @staticmethod
    def json():
        from json import loads, dumps
        return (loads, dumps)

    @staticmethod
    def yaml():
        from yaml import load, dump
        return (load, dump)

    @staticmethod
    def pickle():
        from pickle import loads, dumps
        return (loads, dumps)

    @classmethod
    def loads(cls, fmt, raw):
        loads, _ = getattr(cls, fmt)()
        return loads(raw)

    @classmethod
    def dumps(cls, fmt, raw):
        _, dumps = getattr(cls, fmt)()
        return dumps(raw)
