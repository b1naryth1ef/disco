
class BaseStorageBackend(object):
    def base(self):
        return self.storage

    def __getitem__(self, key):
        return self.storage[key]

    def __setitem__(self, key, value):
        self.storage[key] = value

    def __delitem__(self, key):
        del self.storage[key]


class StorageDict(dict):
    def ensure(self, name):
        if not dict.__contains__(self, name):
            dict.__setitem__(self, name, StorageDict())
        return dict.__getitem__(self, name)
