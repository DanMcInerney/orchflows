"""Reference token-bucket limiter: the exhibited surface, implemented exactly."""


class TokenBucket:
    def __init__(self, rate, burst, clock):
        self._rate = float(rate)
        self._burst = int(burst)
        self._clock = clock
        self._tokens = float(self._burst)
        self._last = clock()

    def acquire(self, n):
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(float(self._burst), self._tokens + elapsed * self._rate)
        self._last = now
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False
