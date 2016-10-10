import os
import gevent

from disco.util.serializer import Serializer
from .base import BaseProvider


class DiskProvider(BaseProvider):
    def __init__(self, config):
        super(DiskProvider, self).__init__(config)
        self.format = config.get('format', 'pickle')
        self.path = config.get('path', 'storage') + '.' + self.format
        self.fsync = config.get('fsync', False)
        self.fsync_changes = config.get('fsync_changes', 1)

        self.change_count = 0

    def autosave_loop(self, interval):
        while True:
            gevent.sleep(interval)
            self.save()

    def _on_change(self):
        if self.fsync:
            self.change_count += 1

            if self.change_count >= self.fsync_changes:
                self.save()
                self.change_count = 0

    def load(self):
        if not os.path.exists(self.path):
            return

        if self.config.get('autosave', True):
            self.autosave_task = gevent.spawn(
                self.autosave_loop,
                self.config.get('autosave_interval', 120))

        with open(self.path, 'r') as f:
            self.data = Serializer.loads(self.format, f.read())

    def save(self):
        with open(self.path, 'w') as f:
            f.write(Serializer.dumps(self.format, self.data))

    def set(self, key, value):
        super(DiskProvider, self).set(key, value)
        self._on_change()

    def delete(self, key):
        super(DiskProvider, self).delete(key)
        self._on_change()
