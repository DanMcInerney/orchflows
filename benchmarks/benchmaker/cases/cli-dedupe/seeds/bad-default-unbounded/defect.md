# bad-default-unbounded

The command layer passes `args.window or 1` to the retention rule, so
the documented default of `0` — unbounded, compare against every
previously retained line — silently becomes a window of 1. Only
adjacent repeats are removed when the tool is invoked with no flags.
Every explicit `--window N` with `N >= 1` is unaffected, so the seed is
byte-identical to the reference on any run that names the flag.

A quality benchmark for a deterministic CLI must catch this because
defaults are the invocation almost every user actually types, and a
default that silently means something else is the most expensive class
of CLI defect. Catching it requires exercising the tool with no flags on
input whose repeats are *not* adjacent — the one shape a fixture full of
`a a b b` runs never produces. The seed is the cheap end of this case's
discrimination range: any benchmark that fails to catch it has not
tested the tool's default behaviour at all.
