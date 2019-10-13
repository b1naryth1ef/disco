import gevent

from collections import defaultdict
from gevent.event import AsyncResult
from gevent.queue import Queue, Full


class Priority(object):
    # BEFORE is the most dangerous priority level. Every event that flows through
    #  the given emitter instance will be dispatched _sequentially_ to all BEFORE
    #  handlers. Until these before handlers complete execution, no other event
    #  will be allowed to continue. Any exceptions raised will be ignored.
    BEFORE = 1

    # AFTER has the same behavior as before with regards to dispatching events,
    #  with the one difference being it executes after all the BEFORE listeners.
    AFTER = 2

    # SEQUENTIAL guarantees that all events your handler receives will be ordered
    #  when looked at in isolation. SEQUENTIAL handlers will not block other handlers,
    #  but do use a queue internally and thus can fall behind.
    SEQUENTIAL = 3

    # NONE provides no guarantees around the ordering or execution of events, sans
    #  that BEFORE handlers will always complete before any NONE handlers are called.
    NONE = 4

    ALL = {BEFORE, AFTER, SEQUENTIAL, NONE}


class Event(object):
    def __init__(self, parent, data):
        self.parent = parent
        self.data = data

    def __getattr__(self, name):
        if hasattr(self.data, name):
            return getattr(self.data, name)
        raise AttributeError


class EmitterSubscription(object):
    def __init__(self, events, callback, priority=Priority.NONE, conditional=None, metadata=None, max_queue_size=8096):
        self.events = events
        self.callback = callback
        self.priority = priority
        self.conditional = conditional
        self.metadata = metadata or {}
        self.max_queue_size = max_queue_size

        self._emitter = None
        self._queue = None
        self._queue_greenlet = None

        if priority == Priority.SEQUENTIAL:
            self._queue_greenlet = gevent.spawn(self._queue_handler)

    def __del__(self):
        if self._emitter:
            self.detach()

        if self._queue_greenlet:
            self._queue_greenlet.kill()

    def __call__(self, *args, **kwargs):
        if self._queue is not None:
            try:
                self._queue.put_nowait((args, kwargs))
            except Full:
                # TODO: warning
                pass
            return

        if callable(self.conditional):
            if not self.conditional(*args, **kwargs):
                return
        return self.callback(*args, **kwargs)

    def _queue_handler(self):
        self._queue = Queue(self.max_queue_size)

        while True:
            args, kwargs = self._queue.get()
            try:
                self.callback(*args, **kwargs)
            except Exception:
                # TODO: warning
                pass

    def attach(self, emitter):
        self._emitter = emitter

        for event in self.events:
            self._emitter.event_handlers[self.priority][event].append(self)

        return self

    def detach(self, emitter=None):
        emitter = emitter or self._emitter

        for event in self.events:
            if self in emitter.event_handlers[self.priority][event]:
                emitter.event_handlers[self.priority][event].remove(self)

    def remove(self, emitter=None):
        self.detach(emitter)


class Emitter(object):
    def __init__(self):
        self.event_handlers = {
            k: defaultdict(list) for k in Priority.ALL
        }

    def emit(self, name, *args, **kwargs):
        # First execute all BEFORE handlers sequentially
        for listener in self.event_handlers[Priority.BEFORE].get(name, []):
            try:
                listener(*args, **kwargs)
            except Exception:
                pass

        # Next execute all AFTER handlers sequentially
        for listener in self.event_handlers[Priority.AFTER].get(name, []):
            try:
                listener(*args, **kwargs)
            except Exception:
                pass

        # Next enqueue all sequential handlers. This just puts stuff into a queue
        #  without blocking, so we don't have to worry too much
        for listener in self.event_handlers[Priority.SEQUENTIAL].get(name, []):
            listener(*args, **kwargs)

        # Finally just spawn for everything else
        for listener in self.event_handlers[Priority.NONE].get(name, []):
            gevent.spawn(listener, *args, **kwargs)

    def on(self, *args, **kwargs):
        return EmitterSubscription(args[:-1], args[-1], **kwargs).attach(self)

    def once(self, *args, **kwargs):
        result = AsyncResult()
        li = None

        def _f(e):
            result.set(e)
            li.detach()

        li = self.on(*args + (_f, ))

        return result.wait(kwargs.pop('timeout', None))

    def wait(self, *args, **kwargs):
        result = AsyncResult()
        match = args[-1]

        def _f(e):
            if match(e):
                result.set(e)

        return result.wait(kwargs.pop('timeout', None))
