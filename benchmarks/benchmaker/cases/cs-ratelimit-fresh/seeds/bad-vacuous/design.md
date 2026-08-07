# Frozen evaluation design — token-bucket limiter benchmark

Boundary: the exhibited surface only — `TokenBucket(rate, burst, clock)`
and `acquire(n) -> bool`, per `interface.md`. No case may invoke any
other identifier on the limiter.

Clock law: every case runs against an injected scripted clock; the
scoring path never sleeps and never reads a real clock. The two
exhibited timelines (T1, T2) are carried verbatim as anchored cases;
three further cases exercise the refill law after idle time, the burst
cap at exact full refill, and consume-nothing-on-denial.

Scoring law: five cases, all required; any required failure fails the
implementation. Verdicts are deterministic — same implementation, same
verdict, on every host.
