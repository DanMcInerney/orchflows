"""Equivalent limiter with different internals: tracks the deficit, not the level."""


class TokenBucket:
    def __init__(self, rate, burst, clock):
        self._rate = float(rate)
        self._capacity = float(int(burst))
        self._clock = clock
        self._deficit = 0.0  # tokens missing from a full bucket
        self._stamp = clock()

    def acquire(self, n):
        now = self._clock()
        repaid = (now - self._stamp) * self._rate
        if repaid > 0:
            self._deficit = self._deficit - repaid
            if self._deficit < 0.0:
                self._deficit = 0.0
        self._stamp = now
        if self._capacity - self._deficit >= n:
            self._deficit += n
            return True
        return False
