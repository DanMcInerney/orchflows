"""token_bucket - a token-bucket rate limiter over an injected clock.

The behavioural contract lives in ``evidence/spec.md``. This file is the
reference implementation of that contract.
"""

VERSION = "1.2.0"

#: Slack absorbed when comparing accumulated float tokens against a cost.
TOLERANCE = 1e-9


class TokenBucket(object):
    """A bucket of ``capacity`` tokens refilled at ``refill_per_second``.

    ``clock`` is a zero-argument callable returning monotonically
    non-decreasing seconds. It is the only source of time the bucket may
    read.
    """

    def __init__(self, capacity, refill_per_second, clock, tokens=None):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be >= 0")
        if not callable(clock):
            raise TypeError("clock must be a zero-argument callable")
        self._capacity = float(capacity)
        self._rate = float(refill_per_second)
        self._clock = clock
        start = self._capacity if tokens is None else float(tokens)
        self._tokens = min(self._capacity, max(0.0, start))
        self._last = float(clock())

    def _refill(self):
        now = float(self._clock())
        elapsed = now - self._last
        if elapsed > 0.0:
            self._tokens = self._tokens + elapsed * self._rate
        self._last = now

    def allow(self, cost=1):
        """Refill, then consume ``cost`` tokens if they are available."""
        if cost <= 0:
            raise ValueError("cost must be > 0")
        self._refill()
        if self._tokens + TOLERANCE >= cost:
            self._tokens = max(0.0, self._tokens - cost)
            return True
        return False
