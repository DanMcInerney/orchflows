"""Defective limiter: the bucket never refills; tokens only ever decrease."""


class TokenBucket:
    def __init__(self, rate, burst, clock):
        self._rate = float(rate)
        self._burst = int(burst)
        self._clock = clock
        self._tokens = float(self._burst)

    def acquire(self, n):
        self._clock()  # the clock is read but its advance is discarded
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False
