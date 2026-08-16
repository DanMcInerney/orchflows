---
id: 05-measure
executor: orch-verify
depends_on: [04-audit]
write_scope: [{{package}}]
bound: <= 40 tool calls
excluded_actions:
  - compare candidates
  - promote or activate anything
  - call Evolve
  - close without recording the qualified result in the package's manifest, whose field set and component resolution are its own, at the git revision the benchmark sits at
independence: checker
isolation: none
profile: orch-worker
---

## Objective

The manifest recorded, and the measurement pass beside it: what the
candidates scored over the candidate-accessible scope at the declared
rungs, as a recording that cannot fail and so forces no revision loop.

## Fixed inputs

- 04-audit's `## Result` — the audit and attack records, and the
  repaired assembly.
- 03-qualify's `## Result` — the verdict set the manifest's
  `qualification` component names.
- [the manifest](../references/benchmaker-manifest.md) — the field set,
  and how a component reference resolves.
- [the protocol](../references/benchmaker-protocol.md)'s measurement
  pass — what is declared before running, the three-valued per-case
  status, and the record that lands outside the package.

## Completion test

- the manifest's qualification verdict set covers every component but its own — covered PASS on every required criterion, gaps explicit (`[]` when none) | oracle: the manifest read against its own field set and the verdict set | oracle_class: deterministic | provenance: pre-existing
- the measurement record lands outside the package naming a default-branch-reachable revision carrying identical measured bytes, the full candidate identity, the date, the measured scope, and the per-case three-valued status with its distinct failure signature count | oracle: the measurement record | oracle_class: deterministic | provenance: authored-here
- every protocol-required criterion the dispatched authority made unreachable is recorded as an intake gap before scoring, never as a candidate failure | oracle: the declared authority beside the gap list | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the benchmark's revision; verification — the
qualification; then gaps (`[]` when none), bounds spent, and changed
artifacts; failure carries partial evidence in qualification and gaps

## Result

## Verification

## Feedback

[]

## Risks

[]
