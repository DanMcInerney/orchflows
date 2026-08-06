# Composition contract

A named workflow over dispatchable units — skills and other
compositions — combined by the combinators; each unit returns one
result envelope per [result.md](result.md). Nesting is one level: a
step may name a composition whose own steps name only skills.

- `name`, `description` (≤140 chars) — the routing and name surface,
  minted into host stubs.
- `entry` — `routed` | `named` | `scheduled`: routed sits in the
  intake table per [rules/topology.md](../rules/topology.md) §2;
  named runs only when named; scheduled runs on its schedule trigger.
- `steps` — each: `id`; `unit` — a skill or composition; `pack` — set
  when the unit takes a stamped spec; frozen bindings — done-check,
  context packet, lens, profile, an optional `when` skip condition —
  fixed at authoring, never chosen mid-run.
- `edges` — the combinators over step ids: `seq` — the predecessor's
  `result` identity becomes the successor spec's `evidence`; `par` —
  branches hold disjoint write scopes and meet at a named join —
  check, reduction, or adjudication; `loop` — body plus done-check
  plus bound, dispatched through `orch-loop`.
- `invariants` — the `Never:` block binding every step.
- `done_check` — the end-to-end oracle over the final envelope: a
  chain of individually gated runs has no gate over the whole; this
  field is that gate.
- `Require:` / `Return:` — envelope law as any skill: `Return:` leads
  with the result envelope.

Detail beyond the body lives in the composition's own `references/`,
as in a skill package.

Admission through `orch-build` rejects a composition missing
`invariants` or `done_check`, or with a step no invariant binds.

Runtime instances: a multi-run request materializes an unnamed
instance at `.orch/runs/<run>/composition.md` — chains and saved
workflows share this one representation, and cross-session resumption
reads it.
