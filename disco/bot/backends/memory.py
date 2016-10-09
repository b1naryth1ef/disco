from .base import BaseStorageBackend, StorageDict


class MemoryBackend(BaseStorageBackend):
    def __init__(self, config):
        self.storage = StorageDict()

