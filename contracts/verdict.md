# Verdict contract

The grammar every oracle emits and every verification, judgment, and gate
consumes. Vocabulary: [docs/vocabulary.md](../docs/vocabulary.md).

Per criterion:

- `verdict`: `PASS` | `FAIL` | `UNVERIFIED`. An unrun check is UNVERIFIED,
  never FAIL and never assumed PASS.
- `oracle`: the exact named check that produced the verdict — a command, a
  rubric reference, or a source-resolution procedure.
- `oracle_class`: `deterministic` | `judged` | `evidence`.
- `evidence`: what the oracle actually produced, quoted or cited by
  identity. A verdict without evidence is UNVERIFIED.
- `covers`: the base, result, and dependency identities the verdict holds
  for. A verdict is invalidated when anything it covers changes.

Overall verdict: PASS only when every required criterion is PASS, and it
states the weakest oracle_class it contains. Every criterion in a spec's
acceptance and a ticket's completion test is required unless the spec
explicitly marks it optional; nothing downstream may reclassify one.

Class policy, wired into every loop and gate:

- `deterministic` — an executable check. May loop until green within
  bounds; green is green.
- `judged` — model judgment against a lens. Budget-bounded; a run never
  ends on its own claimed green; the final gate re-judges fresh from the
  spec, never from prior claims.
- `evidence` — source-backed. Every citation must resolve, and each
  resolved source must support the claim it is cited for.
