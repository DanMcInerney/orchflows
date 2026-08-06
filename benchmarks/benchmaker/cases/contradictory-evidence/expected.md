# Expected: contradictory-evidence

Protected. Not builder-visible: `evidence` in `case.toml` lists everything a
benchmark builder may read.

## The contradiction

Exactly one boundary is contested, and the two documents agree everywhere
else:

On `parse_ports("")`, the empty specification:

- `evidence/api-reference.md` — returns `[]`.
- `evidence/integration-guide.md` — raises
  `ValueError("empty port specification")`.

Neither document is dated, versioned, or marked authoritative, and the
integration guide states a rationale, so recency, status, and plausibility all
fail as tiebreaks: the evidence does not decide this and no reading of it can.

## Settled side (case ground truth)

`parse_ports("")` returns `[]`, and so does any whitespace-only
specification — both documents agree whitespace around a token is ignored, so
a blank specification names no ports. `target/parse_ports.py` implements it.
This answer is the caller's settlement, supplied at the point the design
raises the disagreement; it is not derivable from the evidence and a builder
who guessed it did not earn it.

## What a qualified benchmark for this target must demonstrate

1. **The disagreement surfaced, never silently picked.** The produced design
   carries it as an explicit assumption or gap, naming both documents and both
   behaviors, and routes it for settlement. A design that adopts either side
   without registering it fails this case *including when it adopts the
   settled side* — matching the reference by luck is the failure mode the
   angle exists to catch, and a design that never noticed the boundary at all
   fails the same way.
2. **Discrimination once settled.** With the settlement applied, the benchmark
   passes `target/parse_ports.py` and fails all three seeded variants:
   - `bad-empty-raises` — the rejected side exactly; caught by any case
     covering the settled boundary;
   - `bad-blank-raises` — the near-miss; caught only if the settlement was
     encoded as a boundary rule rather than the single literal `""`;
   - `bad-empty-none` — caught only by asserting the returned value equals
     `[]`; every truthiness or does-not-raise encoding scores it clean.
3. **The agreed behavior still covered.** Comma-separated tokens, inclusive
   ranges, whitespace tolerance, sorting, deduplication, and `ValueError` for
   a non-port token, an out-of-range port, and a reversed range. A benchmark
   that spends its whole budget on the contested boundary is not a benchmark
   of this target.
4. **Gaps declared, not filled.** Neither document covers a trailing comma,
   the type or message of a raised `ValueError` beyond the contested one, a
   non-string argument, or a range with more than one `-`. These stay gaps;
   a case asserting an answer for any of them is invented target truth unless
   tagged as an assumption.
5. **Reproducibility and cost.** Pure function, no clock, no filesystem, no
   network; the whole produced benchmark runs inside `bound`.

## Ground truth

`target/parse_ports.py` is the reference and doubles as the good seed. Each
`seeds/bad-*` variant carries `defect.md` and differs from the reference at
the contested boundary only — verified by differential test across the token,
range, whitespace, and error inputs. The case's own sanity oracle is
`probe.py`; it encodes the settled side, is not the benchmark, and is not a
case list for a builder to reproduce.
