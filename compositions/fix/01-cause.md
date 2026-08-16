---
id: 01-cause
executor: orch-loop
pack: orch-code-pack
depends_on: [00-reproduce]
write_scope: []
bound: <= 8 iterations
excluded_actions:
  - repairing the cause once it is proven
  - changing any artifact in {{workspace}} (the toggle is shown in a throwaway clone beside it)
independence: checker
isolation: none
profile: orch-worker
---

## Objective

One proven cause of {{failure}}: the single change that, toggled,
toggles the reproduction between FAIL and PASS.

## Fixed inputs

- 00-reproduce's `## Result` — the reproduction command, the revision it
  was run at, and the failure identity, by identity.
- Body: orch-investigate over exactly one hypothesis per iteration —
  the hypothesis stated as a prediction the reproduction can falsify.
- Context packet: the killed-hypothesis digest — each hypothesis tried,
  the observation that killed it, and what it rules out; never the
  transcript.

## Completion test

- done-check: the candidate cause toggled toggles the failure — the reproduction FAILs with it present and PASSes with it toggled, at the same revision | oracle: the reproduction command from 00-reproduce's Result, run at both toggle states | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the proven cause by identity, the toggle that
demonstrates it, and the killed-hypothesis digest; verification;
feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
