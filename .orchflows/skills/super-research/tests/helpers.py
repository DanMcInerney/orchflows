"""Shared test scaffolding: one fake clock, one offline carrier, two guards.

Nothing here is a test, and no suite is required to use it. It exists because
a rate budget cannot be proven by waiting: a route measured at one request per
thirty seconds would cost a suite thirty real seconds per read, so the only
honest proof advances a clock instead.

``FakeClock`` is the load-bearing part. One object drives three things at once
— the monotonic seconds a cache reads, the monotonic seconds a governor paces
on, and the ISO stamp a transport writes onto a response — so a moment
fabricated anywhere is visibly different from the moment the origin was really
read, and a wait is a number rather than a delay.
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import io
import os
import socket
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from unittest import mock

from super_research import transport

# The moment every fake run starts from. Frozen, so a recorded observation time
# is comparable across suites and across runs of the same suite.
FROZEN_START = "2026-08-10T09:00:00Z"
STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
US_PER_SECOND = 1000000

# What one origin read costs when a route declares nothing better. Small enough
# that it never dominates a pacing proof, nonzero so every operation has a
# duration and every schedule has a makespan.
DEFAULT_LATENCY_SECONDS = 0.25


class FakeClock:
    """One clock for TTL arithmetic, pacing, and the transport's wall stamp.

    Microseconds are the base unit because a ledger tick is an integer
    microsecond; seconds are derived, so the two can never disagree by
    rounding. ``sleep`` is the whole reason a governor can be tested at all:
    it is a wait that moves time without spending any.
    """

    def __init__(self, start=FROZEN_START):
        self._start = datetime.strptime(start, STAMP_FORMAT).replace(tzinfo=timezone.utc)
        self.microseconds = 0

    @property
    def seconds(self):
        return self.microseconds / float(US_PER_SECOND)

    def advance(self, seconds):
        self.microseconds += int(round(seconds * US_PER_SECOND))

    def sleep(self, seconds):
        """Stand in for ``time.sleep``: the wait happens, the waiting does not."""

        self.advance(seconds)

    def monotonic(self):
        return self.seconds

    def stamp(self):
        return (self._start + timedelta(microseconds=self.microseconds)).strftime(STAMP_FORMAT)


class RecordingOpener:
    """Offline opener: canned answers per route, every attempt recorded.

    A route may be seeded with one answer or with a list of answers consumed in
    order, the last one standing for every later read — which is how a route
    that answers twice and then rate-limits is expressed. Each answer costs its
    route's declared latency on the clock, so an operation's duration is the
    route's measured cost rather than an invention.

    Nothing here can reach a socket, so an unseeded route fails loudly rather
    than egressing.
    """

    def __init__(self, responses, clock=None, latencies=None):
        self.responses = {route: list(answers) if isinstance(answers, list) else [answers]
                          for route, answers in responses.items()}
        self.clock = clock
        self.latencies = dict(latencies or {})
        self.opened = []

    def __call__(self, request):
        self.opened.append(request)
        if request.route_id not in self.responses:
            raise transport.TransportError("no offline response seeded for " + request.route_id)
        answers = self.responses[request.route_id]
        outcome = answers.pop(0) if len(answers) > 1 else answers[0]
        if self.clock is not None:
            self.clock.advance(self.latencies.get(request.route_id, DEFAULT_LATENCY_SECONDS))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def offline_transport(clock, responses, latencies=None):
    """A real carrier whose only fake parts are the opener and the clock."""

    opener = RecordingOpener(responses, clock=clock, latencies=latencies)
    return transport.Transport(opener=opener, now=clock.stamp), opener


class RefusingSocket(socket.socket):
    """A socket that cannot be opened.

    It stays a *subclass* on purpose: ``ssl`` does ``class SSLSocket(socket)``
    at import time, so a guard that swaps ``socket.socket`` for a plain
    function breaks any stdlib module that has not been imported yet.
    """

    def __init__(self, *args, **kwargs):
        raise AssertionError("a socket was opened inside a zero-I/O guard")


@contextlib.contextmanager
def forbid_io():
    """Make every filesystem and socket primitive raise for the guarded block."""

    def refuse(*args, **kwargs):
        raise AssertionError("I/O attempted inside a zero-I/O guard")

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(builtins, "open", refuse))
        stack.enter_context(mock.patch.object(io, "open", refuse))
        stack.enter_context(mock.patch.object(os, "open", refuse))
        stack.enter_context(mock.patch.object(socket, "socket", RefusingSocket))
        stack.enter_context(mock.patch.object(socket, "create_connection", refuse))
        stack.enter_context(mock.patch.object(urllib.request, "urlopen", refuse))
        yield


@contextlib.contextmanager
def forbid_sleep():
    """Make any wall-clock wait raise: pacing is proven by moving a fake clock."""

    def refuse(*args, **kwargs):
        raise AssertionError("a wall-clock wait was attempted inside a fake-clock proof")

    with mock.patch.object(time, "sleep", refuse):
        yield


def imported_names(path):
    """Every module and imported symbol path one source file names in an import."""

    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                names.add(module)
            for alias in node.names:
                names.add(module + "." + alias.name if module else alias.name)
    return names


def attribute_names(path):
    """Every dotted attribute access one source file spells, as ``owner.name``."""

    return {
        node.value.id + "." + node.attr
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }
