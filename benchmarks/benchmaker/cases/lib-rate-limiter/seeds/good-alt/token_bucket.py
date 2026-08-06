"""token_bucket - a token-bucket rate limiter over an injected clock.

Second correct implementation of ``evidence/spec.md``. It shares no
internal structure with the reference: different attribute names, no
``_refill`` helper, and the grant test written as a deficit rather than
a comparison against the cost. Observable behaviour is identical, so a
benchmark that reaches past ``allow`` into the bucket's internals fails
here while a benchmark that tests the contract passes.
"""

VERSION = "1.2.0"

_EPS = 1e-9


class TokenBucket(object):

    def __init__(self, capacity, refill_per_second, clock, tokens=None):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be >= 0")
        if not callable(clock):
            raise TypeError("clock must be a zero-argument callable")
        self._cap = float(capacity)
        self._per_second = float(refill_per_second)
        self._now = clock
        stock = self._cap if tokens is None else float(tokens)
        if stock < 0.0:
            stock = 0.0
        elif stock > self._cap:
            stock = self._cap
        self._stock = stock
        self._stamp = float(clock())

    def allow(self, cost=1):
        if cost <= 0:
            raise ValueError("cost must be > 0")
        moment = float(self._now())
        gained = (moment - self._stamp) * self._per_second
        self._stamp = moment
        if gained > 0.0:
            self._stock += gained
            if self._stock > self._cap:
                self._stock = self._cap
        if self._stock - cost < -_EPS:
            return False
        self._stock -= cost
        if self._stock < 0.0:
            self._stock = 0.0
        return True
