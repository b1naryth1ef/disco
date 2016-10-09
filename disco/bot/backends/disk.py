import os

from .base import BaseStorageBackend, StorageDict


class DiskBackend(BaseStorageBackend):
    def __init__(self, config):
        self.format = config.get('format', 'json')
        self.path = config.get('path', 'storage') + '.' + self.format
        self.storage = StorageDict()

    @staticmethod
    def get_format_functions(fmt):
        if fmt == 'json':
            from json import loads, dumps
            return (loads, dumps)
        elif fmt == 'yaml':
            from pyyaml import load, dump
            return (load, dump)
        raise Exception('Unsupported format type {}'.format(fmt))

    def load(self):
        if not os.path.exists(self.path):
            return

        decode, _ = self.get_format_functions(self.format)

        with open(self.path, 'r') as f:
            self.storage = decode(f.read())

    def dump(self):
        _, encode = self.get_format_functions(self.format)

        with open(self.path, 'w') as f:
            f.write(encode(self.storage))
