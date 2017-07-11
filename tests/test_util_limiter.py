import time
import gevent
from unittest import TestCase

from disco.util.limiter import SimpleLimiter


class TestSimpleLimiter(TestCase):
    def test_many_wait_ratelimiter(self):
        limit = SimpleLimiter(5, 1)
        many = []

        def check(lock):
            limit.check()
            lock.release()

        start = time.time()
        for _ in range(16):
            lock = gevent.lock.Semaphore()
            lock.acquire()
            many.append(lock)
            gevent.spawn(check, lock)

        for item in many:
            item.acquire()

        self.assertGreater(time.time() - start, 3)

    def test_nowait_ratelimiter(self):
        limit = SimpleLimiter(5, 1)

        start = time.time()
        for _ in range(5):
            limit.check()

        self.assertLess(time.time() - start, 1)

    def test_single_wait_ratelimiter(self):
        limit = SimpleLimiter(5, 1)

        start = time.time()
        for _ in range(10):
            limit.check()

        self.assertEqual(int(time.time() - start), 1)
