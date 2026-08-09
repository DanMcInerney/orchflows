deviation: contract-substitution @ scoring-clock locus

The scoring path substitutes the real clock for the injected scripted
clock: every `advance` step is a real `time.sleep` and the limiter
reads `time.monotonic`. The case set spans 154 virtual seconds per
implementation, so the inner sweep cannot complete inside the 30 s
scripted-clock envelope. Everything else is lawful — every component
locator resolves, including the changed runner.

Burn note: `contract-substitution` is a census name; this locus is
constitutionally fresh — the predecessor's real-clock design could not
fail this seed in principle, so the scoring-clock locus was never
burnable before.
