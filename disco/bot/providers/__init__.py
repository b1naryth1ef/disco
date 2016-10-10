import inspect
import importlib

from .base import BaseProvider


def load_provider(name):
    try:
        mod = importlib.import_module('disco.bot.providers.' + name)
    except ImportError:
        mod = importlib.import_module(name)

    for entry in filter(inspect.isclass, map(lambda i: getattr(mod, i), dir(mod))):
        if issubclass(entry, BaseProvider) and entry != BaseProvider:
            return entry
