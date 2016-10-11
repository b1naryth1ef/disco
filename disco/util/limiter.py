import time
import gevent


class SimpleLimiter(object):
    def __init__(self, total, per):
        self.total = total
        self.per = per

        self.count = 0
        self.reset_at = 0

        self.event = None

    def backoff(self):
        self.event = gevent.event.Event()
        gevent.sleep(self.reset_at - time.time())
        self.count = 0
        self.reset_at = 0
        self.event.set()
        self.event = None

    def check(self):
        if self.event:
            self.event.wait()

        self.count += 1

        if not self.reset_at:
            self.reset_at = time.time() + self.per
            return
        elif self.reset_at < time.time():
            self.count = 1
            self.reset_at = time.time()

        if self.count > self.total and self.reset_at > time.time():
            self.backoff()
