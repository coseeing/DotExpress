"""Deterministic stand-ins for the conversion threading seams (no wx, no tests here).

* ``FakeThread`` never runs its target in ``start()``; the test calls ``run()``.
* ``make_thread_factory()`` returns a ``thread_factory`` that records every thread
  it creates in its ``threads`` attribute.
* ``DeferredCalls`` is a ``call_after`` that queues ``(fn, args, kwargs)``; the test
  runs one later UI turn with ``run_next()`` or all of them with ``run_all()``.
* ``FakeTimers`` is a ``call_later(ms, fn, *args)`` that returns a ``FakeTimer`` with
  ``Stop()`` and ``fire()``.

``DeferredCalls`` and ``FakeTimers`` take an optional shared event list and append
``("call_after",)``, ``("call_later", ms, args)`` and ``("timer.Stop", n)`` (``n`` counts
timers from 1) to it, so a test sees the order of effects across UI turns. The
entries carry no function names: the code that queues the call may move.

This module has no ``test_`` prefix, so importing it never runs tests twice.
"""

from __future__ import annotations


class FakeThread:
    def __init__(self, *, target, args=(), daemon=None):
        self._target = target
        self._args = args
        self.daemon = daemon
        self.started = False
        self._alive = False

    def start(self) -> None:
        self.started = True
        self._alive = True

    def is_alive(self) -> bool:
        return self._alive

    def run(self) -> None:
        try:
            self._target(*self._args)
        finally:
            self._alive = False


def make_thread_factory():
    threads: list[FakeThread] = []

    def thread_factory(*, target, args=(), daemon=None) -> FakeThread:
        thread = FakeThread(target=target, args=args, daemon=daemon)
        threads.append(thread)
        return thread

    thread_factory.threads = threads
    return thread_factory


class DeferredCalls:
    def __init__(self, events: list | None = None):
        self.pending: list[tuple] = []
        self._events = events

    def __call__(self, fn, *args, **kwargs) -> None:
        self.pending.append((fn, args, kwargs))
        if self._events is not None:
            self._events.append(("call_after",))

    def run_next(self):
        fn, args, kwargs = self.pending.pop(0)
        return fn(*args, **kwargs)

    def run_all(self) -> int:
        count = 0
        while self.pending:
            self.run_next()
            count += 1
        return count


class FakeTimer:
    def __init__(self, timers: FakeTimers, number: int, delay_ms: int, fn, args: tuple):
        self._timers = timers
        self.number = number
        self.delay_ms = delay_ms
        self.fn = fn
        self.args = args
        self.stopped = False

    def Stop(self) -> None:
        self.stopped = True
        self._timers._record(("timer.Stop", self.number))

    def fire(self):
        return self.fn(*self.args)


class FakeTimers:
    def __init__(self, events: list | None = None):
        self.timers: list[FakeTimer] = []
        self._events = events

    def __call__(self, delay_ms: int, fn, *args) -> FakeTimer:
        timer = FakeTimer(self, len(self.timers) + 1, delay_ms, fn, args)
        self.timers.append(timer)
        self._record(("call_later", delay_ms, args))
        return timer

    def _record(self, event: tuple) -> None:
        if self._events is not None:
            self._events.append(event)
