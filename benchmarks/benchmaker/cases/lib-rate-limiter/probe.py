#!/usr/bin/env python3
"""Case-author sanity oracle for lib-rate-limiter. NOT the benchmark.

Usage (from this case directory):

    uv run --no-project python probe.py [IMPLEMENTATION]

IMPLEMENTATION is a file or a directory holding ``token_bucket.py``; it
may also arrive in the ``CASE_IMPL`` environment variable, and defaults
to ``target/token_bucket.py``. Paths resolve against the caller's
directory and then against this file's own directory, so the probe runs
from the case directory or from the repository root. Exit 0 means the
implementation satisfies every checked clause of ``evidence/spec.md``;
exit 1 names the clauses it violates.
"""
import importlib.util
import os
import sys

IMPL_NAME = "token_bucket.py"
CASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The case package is immutable: never leave a __pycache__ beside a seed,
# where a stale entry could shadow the bytes a later replay is meant to run.
sys.dont_write_bytecode = True


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = os.path.join("target", IMPL_NAME)
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, IMPL_NAME)
        if os.path.isfile(candidate):
            return candidate
    return None


def load(path):
    spec = importlib.util.spec_from_file_location("impl_under_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TokenBucket


class FakeClock(object):
    def __init__(self, start=0.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


def check_full_bucket_grants_exactly_capacity(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(5, 1, clock)
    for i in range(5):
        assert bucket.allow() is True, "burst token %d denied" % (i + 1)
    assert bucket.allow() is False, "burst exceeded capacity"


def check_idle_bucket_saturates_at_capacity(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(5, 1, clock)
    for _ in range(5):
        bucket.allow()
    clock.advance(100.0)
    for i in range(5):
        assert bucket.allow() is True, "post-idle token %d denied" % (i + 1)
    assert bucket.allow() is False, "idling refilled the bucket past capacity"


def check_fractional_refill_accumulates(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(5, 1, clock, tokens=0)
    for step in range(8):
        clock.advance(0.25)
        assert bucket.allow(5) is False, "granted 5 tokens after %.2fs" % (
            0.25 * (step + 1)
        )
    assert bucket.allow(2) is True, "2.0s at 1/s did not accumulate 2 tokens"
    assert bucket.allow(1) is False, "more than 2 tokens had accumulated"


def check_denied_call_still_advances_time(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(10, 1, clock, tokens=0)
    clock.advance(1.0)
    assert bucket.allow(5) is False, "5 tokens granted after 1s at 1/s"
    clock.advance(1.0)
    assert bucket.allow(2) is True, "2 tokens unavailable after 2s at 1/s"
    assert bucket.allow(1) is False, "the denied call's interval was credited twice"


def check_clock_is_the_only_time_source(TokenBucket):
    clock = FakeClock(start=1000.0)
    bucket = TokenBucket(2, 1, clock, tokens=0)
    assert bucket.allow() is False, "granted from an empty bucket"
    clock.advance(5.0)
    assert bucket.allow(2) is True, "injected clock advance produced no refill"
    assert bucket.allow(1) is False, "refill exceeded capacity"


def check_exact_boundary_grants(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(3, 1, clock, tokens=0)
    clock.advance(1.0)
    assert bucket.allow(1) is True, "exactly one refilled token was denied"


def check_denied_call_does_not_consume(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(2, 0, clock, tokens=1)
    assert bucket.allow(2) is False, "granted 2 tokens from a bucket holding 1"
    assert bucket.allow(1) is True, "the denied call consumed tokens"
    assert bucket.allow(1) is False, "bucket was not empty after consuming its token"


def check_cost_above_capacity_never_grants(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(2, 1000, clock, tokens=0)
    clock.advance(100.0)
    assert bucket.allow(3) is False, "granted a cost larger than capacity"


def check_zero_rate_never_refills(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(3, 0, clock, tokens=0)
    clock.advance(1e6)
    assert bucket.allow(1) is False, "a zero-rate bucket refilled"


def check_default_and_clamped_initial_tokens(TokenBucket):
    clock = FakeClock()
    full = TokenBucket(3, 0, clock)
    assert full.allow(3) is True, "bucket did not start full"
    assert full.allow(1) is False, "bucket started with more than capacity"

    over = TokenBucket(2, 0, clock, tokens=10)
    assert over.allow(2) is True, "clamped starting tokens were lost"
    assert over.allow(1) is False, "starting tokens were not clamped to capacity"

    under = TokenBucket(2, 0, clock, tokens=-5)
    assert under.allow(1) is False, "negative starting tokens were not clamped to 0"


def check_sustained_rate_under_float_drift(TokenBucket):
    clock = FakeClock()
    bucket = TokenBucket(1, 10, clock, tokens=0)
    for step in range(50):
        clock.advance(0.1)
        assert bucket.allow(1) is True, "step %d denied its earned token" % step


def check_argument_validation(TokenBucket):
    clock = FakeClock()
    for capacity in (0, -1):
        try:
            TokenBucket(capacity, 1, clock)
        except ValueError:
            pass
        else:
            raise AssertionError("capacity %r accepted" % capacity)
    try:
        TokenBucket(1, -1, clock)
    except ValueError:
        pass
    else:
        raise AssertionError("negative refill_per_second accepted")
    try:
        TokenBucket(1, 1, "not a clock")
    except TypeError:
        pass
    else:
        raise AssertionError("non-callable clock accepted")
    bucket = TokenBucket(2, 1, clock)
    for cost in (0, -1):
        try:
            bucket.allow(cost)
        except ValueError:
            pass
        else:
            raise AssertionError("cost %r accepted" % cost)


CHECKS = [
    check_full_bucket_grants_exactly_capacity,
    check_idle_bucket_saturates_at_capacity,
    check_fractional_refill_accumulates,
    check_denied_call_still_advances_time,
    check_clock_is_the_only_time_source,
    check_exact_boundary_grants,
    check_denied_call_does_not_consume,
    check_cost_above_capacity_never_grants,
    check_zero_rate_never_refills,
    check_default_and_clamped_initial_tokens,
    check_sustained_rate_under_float_drift,
    check_argument_validation,
]


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write(
            "probe: no such implementation: %s\n"
            % (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL"))
        )
        return 2
    try:
        TokenBucket = load(impl)
    except Exception as exc:
        sys.stderr.write("probe FAIL (%s): import raised %r\n" % (impl, exc))
        return 1

    failures = []
    for check in CHECKS:
        name = check.__name__[len("check_"):].replace("_", "-")
        try:
            check(TokenBucket)
        except AssertionError as exc:
            failures.append("%s: %s" % (name, exc))
        except Exception as exc:
            failures.append("%s: raised %r" % (name, exc))

    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl, len(failures)))
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write("probe PASS (%s): %d checks\n" % (impl, len(CHECKS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
