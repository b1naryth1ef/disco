from .base import BaseStorageBackend, StorageDict


class MemoryBackend(BaseStorageBackend):
    def __init__(self):
        self.storage = StorageDict()

    def base(self):
        return self.storage

    def __getitem__(self, key):
        return self.storage[key]

    def __setitem__(self, key, value):
        self.storage[key] = value

    def __delitem__(self, key):
        del self.storage[key]
