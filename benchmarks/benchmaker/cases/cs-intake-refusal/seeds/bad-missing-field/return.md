status: blocked
stage: intake — no stage work started

## Partial evidence

- The packet was audited against the delegation contract's six parts:
  objective, inputs, authority, return_contract and the reply
  identifier are present; the budget part is absent and is named in
  the gap register below.
- evidence/synthesis-offered.md was audited against the packet's
  required synthesis artifact list; the missing artifact is named in
  the gap register below.
- Nothing beyond the packet and the offered synthesis was read.

## Gaps

- The packet's `bounds` part is absent: there is no effort budget to
  partition across stages, so no stage may lawfully start.
- The offered synthesis is deficient for reuse: its `provenance`
  artifact is missing — six of the seven required charter artifacts
  are present — so it is not reusable as supplied.
