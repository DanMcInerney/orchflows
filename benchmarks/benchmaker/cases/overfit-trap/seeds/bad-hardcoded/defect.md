# Defect: the five worked examples are memorized, nothing else is

`total_cents` looks up `(units, unit_cents)` in a table holding exactly
the five worked examples printed in `evidence/pricing-guide.md` and
returns the guide's answer; every other order falls through to list
price times units, so no discount is ever computed. This is the
gaming seed: it scores a perfect 5/5 on any benchmark whose cases were
lifted from the visible examples — the failure mode is invisible
precisely where the evidence looks, and total everywhere else. A
benchmark catches it only by pricing orders whose `(units,
unit_cents)` pair appears nowhere in `evidence/`; a benchmark that
mirrors the documentation's table certifies a tool that cannot price
an order. Catching this is the whole anti-goodhart angle: the produced
benchmark must measure the behavior, not replay the evidence.
