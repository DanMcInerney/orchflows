# Verdict contract

The grammar used when a benchmark or other structured evaluation needs
per-criterion verdicts. Ticket success remains its Goal; this contract does
not add authored ticket criteria. Vocabulary:
[docs/vocabulary.md](../docs/vocabulary.md).

Per criterion:

- `verdict`: `PASS` | `FAIL` | `UNVERIFIED`. An unrun check is UNVERIFIED,
  never FAIL and never assumed PASS.
- `oracle`: the method the evaluator chose and used — a command, a rubric
  reference, or a source-resolution procedure. It is recorded as evidence,
  never authored into the sealed ticket.
- `oracle_class`: `deterministic` | `judged` | `evidence`.
- `evidence`: what the oracle actually produced, quoted or cited by
  identity. A verdict without evidence is UNVERIFIED, and so is a
  criterion frozen without the reading its oracle produced at baseline.
- `covers`: the base, result, and dependency identities the verdict holds
  for. A verdict is invalidated when anything it covers changes.

Overall structured verdict: PASS only when every required evaluation
criterion is PASS, and it states the weakest oracle_class it contains. A
ticket verdict instead asks whether its observable Goal holds without
contradicting factual Context.

Class policy, wired into every structured evaluation that uses this contract:

- `deterministic` — an executable check. May loop until green within
  bounds; green is green.
- `judged` — model judgment against a lens. Budget-bounded; a run never
  ends on its own claimed green.
- `evidence` — source-backed. Every citation must resolve, and each
  resolved source must support the claim it is cited for.
