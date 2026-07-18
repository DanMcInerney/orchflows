# Work-item contract (ticket)

The universal unit of decomposed work: a [delegation packet](delegation.md)
made durable — packet parts ⊕ completion test ⊕ lifecycle ⊕ graph
position. Every decomposition emits work items, every executor consumes
exactly one, every join integrates one. On disk a work item is a markdown
ticket in the local tracker — the one durable record of its dispatch; the
executor writes its result into the same file. There is no external
tracker.

Location: `.orch/tickets/<run>/<id>.md`.

Frontmatter, mapped to packet parts, lifecycle, and graph position:

- `id` — lifecycle: unique within the run; stable once issued.
- `run` — lifecycle: the owning run id.
- `status`: `pending` | `ready` | `claimed` | `suspended` | `complete` |
  `blocked` | `failed` | `limited` — lifecycle. A ticket issued with an
  incomplete `depends_on` starts `pending`, a non-terminal wait state;
  `orch-frontier` owns its exits — to `ready` once every dependency is
  `complete`, to `blocked` once any dependency is `failed`, `blocked`, or
  `limited`. `ready` always requires every `depends_on` id `complete`.
  `suspended` is the other non-terminal wait: the ticket stays claimed,
  resumable from its `## Handoff`. `complete` requires PASS on every
  required criterion; nothing else does. Terminal status — `complete`,
  `blocked`, `failed`, `limited` — is set only by the join
  (`orch-integrate`), never by the executor. Ticket statuses are not the
  run-level `terminal` set ([worklog.md](worklog.md)): `stalled` exists
  only at run level, `suspended` only at ticket level.
- `executor` — graph position: the named skill bound to do the work,
  from the pack's executor cell, the assembly cell for the terminal
  item, or named directly by the orchestrator for an ad-hoc ticket.
- `pack` — optional: the stamped pack whose cells bind this item's
  workspace, oracles, and craft; set by decomposition from the spec's
  stamp, or by the ad-hoc cutter when a pack fits. Absent, no cell
  binding applies and workspace semantics are plain artifact paths.
- `independence` — optional: `gate` | `checker` — the
  [rules/verification.md](../rules/verification.md) §10 source this
  item's `authored-here` acceptance rides; `gate` is set at cut time
  only when a downstream gate re-verifies this item; absent reads
  `checker`.
- `checked_by` — optional, lifecycle: set by the §10 checker context
  when it appends its pass.
- `depends_on` — graph position: list of item ids; empty list when none.
- `write_scope` — packet `authority`: exactly what this item may change,
  in the workspace semantics of the ticket's `pack` — plain artifact
  paths when no pack is named; a strict subset of the run's scope.
  The ticket file's own result sections and `status` are ticket
  bookkeeping, not workspace content, and sit outside `write_scope`: the
  executor writes only `## Result`, `## Verification`, `## Feedback`,
  `## Risks`, and — when suspending — `## Handoff`; the join alone sets
  terminal `status`.
- `excluded_actions` — packet `authority`, optional: named actions this
  item's executor may not take without suspending through the ticket's
  `## Handoff`.
- `bound` — packet `bounds`: the item's effort budget.
- `claimed_by`, `claimed_at` — lifecycle: set on claim. Staleness runs
  on wall clock: a claim older than the item's bound read as a duration
  is stale and reclaimable; when the bound is not a duration, the lease
  defaults to 60 minutes.
- `profile` — packet `profile`, optional: an explicit role override per
  rules/roles.md §4; absent, role resolves from the executor's declared
  role.

Body sections, in order — completion test plus the packet's remaining
parts:

- `## Objective` — packet `objective`: one observable end state, never
  activities.
- `## Fixed inputs` — packet `inputs`: evidence by identity, never prose
  copies. An item carries verbatim every spec field its executor's
  Require names.
- `## Completion test` — enumerated criteria, each naming its oracle and
  oracle_class per [verdict.md](verdict.md), and optionally its oracle
  provenance — `pre-existing` (the oracle exists or is concretely
  specified before the unit's work) or `authored-here` (the executing
  context creates it); absent reads `authored-here`. Independence law:
  [rules/verification.md](../rules/verification.md) §10.
- `## Return fields` — packet `return_contract`: the named fields the
  executor's result must carry.
- `## Result` — written by the executor: what changed, by identity. A
  §10 checker appends its own pass — findings, changes, invalidated
  entries — and never rewrites the executor's.
- `## Verification` — verdict entries, one per criterion.
- `## Feedback` — bounded observations; `[]` when none.
- `## Risks` — `[]` when none.
- `## Handoff` — optional: the suspension, resumption, or escalation
  record — the reason (the excluded action hit, or why a larger topology
  is needed), remaining scope and known gaps, and budget state per
  bound. A handoff is complete when a fresh agent can resume from it
  without reading the suspended agent's transcript. Suspension and
  escalation each happen at most once per ticket; a second is a
  terminal `blocked`. Compact to identities and verdicts; redact
  transcript prose. On resumption, accepted evidence stays accepted —
  re-verify only entries the handoff marks unverified or invalidated.

Filing law: results land as cited artifacts in the ticket — or the store
the packet names — never as extra return fields; the closing message
delivers the completed ticket or points to it, per rules/delegation.md
§10.

Compatibility floor: the nine frontmatter keys above (id, run, status,
executor, depends_on, write_scope, bound, claimed_by, claimed_at) and
the eight body section names are unchanged on disk; `profile`,
`excluded_actions`, `suspended`, `## Handoff`, per-criterion oracle
provenance, `pack`, `independence`, and `checked_by` are optional
additions — `scripts/tickets.py` and every existing ticket keep
parsing.

Rules: uncovered remainder belongs to the run worklog, never to a ticket;
a ticket never widens its own scope or bound; domains extend the sections,
never replace them.
