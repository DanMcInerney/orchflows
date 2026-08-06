# lib-rate-limiter — what a qualified benchmark must demonstrate

Angle: **time-semantics**. This case tests whether benchmaker produces a
benchmark that *controls* time rather than waiting on it. Every seed
here is invisible to a benchmark that lets real time drive the target.

## Discrimination (required)

The produced benchmark must score `target/token_bucket.py` and
`seeds/good-alt/token_bucket.py` as passing and each of these as
failing:

| seed | reachable only through |
| --- | --- |
| `bad-wall-clock` | a clock the benchmark advances itself, plus an assertion that advancing it changes the answer |
| `bad-refill-rounding` | clock steps smaller than one token, with a call on each step |
| `bad-double-credit` | a denial and a later grant on the same instance, separated by clock movement |
| `bad-burst-edge` (near-miss) | an idle interval past saturation followed by a burst larger than capacity |

`seeds/good-alt` is a second correct implementation with different
attribute names, no refill helper, and a different arrangement of the
grant test. A benchmark that asserts on token counters or calls internal
helpers fails good-alt and is not qualified: `allow`'s boolean return is
the outcome under test.

Failing the near-miss is the case's discrimination floor. A benchmark
that injects a clock but only ever advances it by one refill period
catches `bad-wall-clock` and nothing else — it has proved the target
reads the clock, not that it obeys the contract's ceiling.

## The angle law

Clock injection is not a stylistic preference here. A benchmark that
passes `time.monotonic` as the clock, or that sleeps, is
*constitutionally* unable to fail `bad-wall-clock`: under a real clock
the seed and the reference are the same program. The same benchmark also
cannot reach saturation, sub-token steps, or long idles without spending
real seconds it does not have. Controlling time is simultaneously the
discrimination requirement and the cost requirement.

## Reproducibility

With an injected clock the target is a pure function of its
construction arguments and its call sequence. The produced benchmark
must be free of `sleep`, real clocks, randomness, network, and
filesystem state; repeated runs on the same implementation must yield
identical verdicts on every platform.

Float accumulation is a real hazard: the contract grants when
`tokens + 1e-9 >= cost`, and a benchmark whose expectations assume exact
decimal arithmetic will produce flaky verdicts on the reference itself.
Fixed clock increments and the documented tolerance are the way through.

## Cost

Within `bound`: under 5 s wall clock, at most 25 cases, and no case may
wait on real time. A benchmark that sleeps to observe a refill violates
the bound even when its assertions are right.

## Gaps

None. `evidence/spec.md` fixes the refill rule, the ceiling, the
timestamp-commit rule, the tolerance, and the clock-injection
requirement; `evidence/usage.md` shows both the production and the
under-test call shapes. A blocked or gap-declaring return is the wrong
answer for this case.
