import gevent
from unittest import TestCase

from disco.voice.queue import PlayableQueue


class TestPlayableQueue(TestCase):
    def test_append(self):
        q = PlayableQueue()
        q.append(1)
        q.append(2)
        q.append(3)

        self.assertEqual(q._data, [1, 2, 3])
        self.assertEqual(q.get(), 1)
        self.assertEqual(q.get(), 2)
        self.assertEqual(q.get(), 3)

    def test_len(self):
        q = PlayableQueue()

        for idx in range(1234):
            q.append(idx)

        self.assertEqual(len(q), 1234)

    def test_iter(self):
        q = PlayableQueue()

        for idx in range(5):
            q.append(idx)

        self.assertEqual(sum(q), 10)

    def test_blocking_get(self):
        q = PlayableQueue()
        result = gevent.event.AsyncResult()

        def get():
            result.set(q.get())

        gevent.spawn(get)
        q.append(5)
        self.assertEqual(result.get(), 5)

    def test_shuffle(self):
        q = PlayableQueue()

        for idx in range(10000):
            q.append(idx)

        self.assertEqual(q._data[0], 0)
        q.shuffle()
        self.assertNotEqual(q._data[0], 0)

    def test_clear(self):
        q = PlayableQueue()

        for idx in range(100):
            q.append(idx)

        self.assertEqual(q._data[0], 0)
        self.assertEqual(q._data[-1], 99)
        self.assertEqual(len(q), 100)
        q.clear()
        self.assertEqual(len(q), 0)
