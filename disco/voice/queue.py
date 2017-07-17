import abc
import six
import gevent
import random


@six.add_metaclass(abc.ABCMeta)
class BaseQueue(object):
    @abc.abstractmethod
    def get(self):
        raise NotImplementedError


class PlayableQueue(BaseQueue):
    def __init__(self):
        self._data = []
        self._event = gevent.event.Event()

    def append(self, item):
        self._data.append(item)

        if self._event:
            self._event.set()
            self._event = None

    def _get(self):
        if not len(self._data):
            if not self._event:
                self._event = gevent.event.Event()
            self._event.wait()
            return self._get()
        return self._data.pop(0)

    def get(self):
        return self._get()

    def shuffle(self):
        random.shuffle(self._data)

    def clear(self):
        self._data = []

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self._data.__iter__()

    def __nonzero__(self):
        return True
