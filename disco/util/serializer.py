import six
import types


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


def dump_cell(cell):
    return cell.cell_contents


def load_cell(cell):
    if six.PY3:
        return (lambda y: cell).__closure__[0]
    else:
        return (lambda y: cell).func_closure[0]


def dump_function(func):
    if six.PY3:
        return (
            func.__code__,
            func.__name__,
            func.__defaults__,
            list(map(dump_cell, func.__closure__)) if func.__closure__ else [],
        )
    else:
        return (
            func.func_code,
            func.func_name,
            func.func_defaults,
            list(map(dump_cell, func.func_closure)) if func.func_closure else [],
        )


def load_function(args):
    code, name, defaults, closure = args
    closure = tuple(map(load_cell, closure))
    return types.FunctionType(code, globals(), name, defaults, closure)
