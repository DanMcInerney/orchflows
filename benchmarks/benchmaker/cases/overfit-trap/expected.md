# What a qualified benchmark for overfit-trap must demonstrate

## The measured failure

**A benchmark built only from the examples visible in `evidence/`
cannot catch `bad-hardcoded`.** That seed returns the guide's answer
for each of the five worked examples and list price times units for
everything else. Scored on those five inputs it is indistinguishable
from the reference — 5/5, no signal, and it cannot price a single
order that is not already printed in the documentation. The same
example set also scores `bad-round-half` 5/5, because every worked
example uses a list price of 250, 400 or 1000, on which flooring and
rounding agree. An evidence-mirroring benchmark therefore catches 1 of
3 seeds and certifies two broken tools.

This is the case's whole point: discrimination here is a property of
*case selection*, not of oracle strictness. A perfectly strict
exact-integer oracle run on the documented inputs still fails.

## Required of the produced benchmark

1. **Inputs beyond the evidence.** At least one case whose `(units,
   unit_cents)` pair appears in neither `evidence/pricing-guide.md`
   nor `evidence/support-faq.md`. Without this the benchmark scores
   `bad-hardcoded` as a pass and discrimination is UNVERIFIED, no
   matter how many cases it has.
2. **A fractional-cent case.** At least one order whose discounted
   band subtotal is not a whole cent — a list price that is not a
   multiple of ten, at a quantity reaching the volume or bulk band
   (16 at 199 and 64 at 175 both work). This is the only input class
   that separates flooring from rounding, and the evidence contains
   none.
3. **All three bands, and their boundaries.** Cases covering the
   starter band, the volume band, and the bulk band, including the
   9/10 and 49/50 transitions, so a band-assignment defect cannot
   hide.
4. **An exact-integer oracle.** The expected total is a fixed integer
   compared for equality; no tolerance, no "about", no substring
   match on the CLI output.
5. **Error cases.** Zero and negative units or list price raise
   `ValueError`.
6. **Discrimination stated as a score.** The qualification record
   names each seed and its verdict; every `bad-*` seed fails at least
   one case and `good-banded` passes every case. A benchmark that
   fails `good-banded` is scoring implementation shape and is not
   qualified.
7. **Reproducibility.** `total_cents` is a pure integer function: two
   runs of the benchmark produce identical verdicts on the same bytes.
   No clock, no seed, no environment.
8. **Cost within bound.** The whole run stays inside `case.toml`'s
   bound — at most 12 cases, under 5 s. Exhaustive sweeps over the
   input space are a cost failure, not thoroughness.

## Protected evidence

`seeds/` is ground truth for scoring the produced benchmark and is
never referenced by `evidence/`, by `target/`, or by the probe's
inputs; a builder that has read `seeds/bad-hardcoded/` has invalidated
the measurement, since the trap is precisely whether it generalizes
past what it was shown.
