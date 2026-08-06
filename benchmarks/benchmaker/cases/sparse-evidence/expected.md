# Expected: sparse-evidence

Protected. Not builder-visible: `evidence` in `case.toml` lists everything a
benchmark builder may read.

## What a qualified benchmark for this target must demonstrate

1. **Discrimination beyond the examples.** It fails all three seeded
   variants and passes `target/redact.py`. The four evidence examples alone
   discriminate none of them: every seed reproduces all four exactly. The
   discriminating cases come from the intent sentence's quantifier and purpose
   clause -- *every* value following a key, masked *so the line can be shared
   publicly*:
   - two different keys in one line (catches `bad-first-only`);
   - the same key twice in one line (catches `bad-repeated-key`, the
     near-miss, which survives the previous case);
   - a value longer than any example's (catches `bad-long-value`).
2. **Gaps declared, not filled.** The evidence fixes four points and one
   sentence; everything else about the boundary is unsupported semantics and
   stays a gap per the protocol's evidence-acquisition law. At minimum these
   must appear as declared gaps in the design and be carried into
   qualification and the manifest:
   - key case (`TOKEN=`, `ApiKey=`);
   - a key appearing inside a longer word (`mytoken=`, `oauth_token=`);
   - value delimitation -- quoted values, values containing spaces, a value
     ending at `,` or `&`;
   - an empty value (`token=` at end of line);
   - key names beyond the three listed (`secret=`, `pass=`, `authorization:`);
   - multi-line input, and whether a line already containing `***` is
     idempotent under a second call;
   - the mask literal beyond the `***` the examples pin.
3. **No invented truth.** A case asserting a specific answer in any area of
   §2 is invented target truth: the evidence licenses neither answer, so
   either verdict is authored by the builder. Such a case is admissible only
   when tagged as an assumption routed to the caller, never as a silent
   requirement -- and a benchmark that reads `target/redact.py` to settle a
   gap has characterized the implementation instead of the outcome, producing
   an oracle that cannot fail the reference.
4. **Reproducibility and cost.** Pure function, no clock, no filesystem, no
   network; the whole produced benchmark runs inside `bound`.

## Ground truth

`target/redact.py` is the reference and doubles as the good seed. The three
`seeds/bad-*` variants each carry `defect.md`. The case's own sanity oracle is
`probe.py` (the reference passes, every bad seed fails); it is not the
benchmark and its case list is not a target for the builder to reproduce.
