import time
import gevent


class SimpleLimiter(object):
    def __init__(self, total, per):
        self.total = total
        self.per = per
        self._lock = gevent.lock.Semaphore(total)

        self.count = 0
        self.reset_at = 0
        self.event = None

    def check(self):
        self._lock.acquire()

        def _release_lock():
            gevent.sleep(self.per)
            self._lock.release()

        gevent.spawn(_release_lock)
