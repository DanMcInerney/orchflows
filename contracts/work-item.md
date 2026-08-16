# Work-item contract (ticket)

The one unit of work, plan, and record: a delegation packet made durable
— packet parts ⊕ completion test ⊕ lifecycle ⊕ graph position. Every
decomposition emits work items, every executor consumes exactly one,
every join integrates one. On disk a work item is a markdown ticket in
the local tracker — the one durable record of its dispatch; the executor
writes its result into the same file. There is no external tracker.

Location: `<state-root>/tickets/<run>/<id>.md`, where the state root is the
user-scope sink `scripts/state_root.py` resolves — one per user, outside
every repository. One run's tickets have exactly one path, identical from
the orchestrator, from every executor workspace, after any workspace is
removed, and after the repository is removed. A dispatch names this path
absolutely; an `excluded_actions` that forbids a directory always carves
out the run's own directory in the sink, since the executor is required to
write its Result there.

## Frontmatter

Mapped to packet parts, lifecycle, and graph position:

- `id` — lifecycle: unique within the run; stable once issued.
- `run` — lifecycle: the owning run id.
- `status`: `pending` | `ready` | `claimed` | `suspended` | `complete` |
  `blocked` | `failed` | `limited` — lifecycle; transitions per
  `orch-frontier`. `pending` and `suspended` are the two non-terminal
  waits: a ticket issued with an incomplete `depends_on` starts
  `pending`; a suspended ticket stays claimed, resumable from its
  `## Handoff`. `complete` requires PASS on every required criterion;
  nothing else does. Terminal status — `complete`, `blocked`, `failed`,
  `limited` — is set only by the join (`orch-integrate`), never by the
  executor. Ticket statuses are not the run-level `terminal` set
  ([worklog.md](worklog.md)): `stalled` exists only at run level,
  `suspended` only at ticket level.
- `executor` — graph position: the named skill or script bound to do the
  work, per Executor form below; from the pack's executor cell, the
  assembly cell for the terminal item, or named directly by the
  orchestrator for an ad-hoc ticket.
- `pack` — optional: the stamped pack whose cells bind this item's
  workspace, oracles, and craft; set by decomposition from the root
  ticket's stamp, or by the ad-hoc cutter when a pack fits. Absent, no
  cell binding applies and workspace semantics are plain artifact paths.
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
  terminal `status`. A §10 checker corrects inside this same
  `write_scope`, per [rules/verification.md](../rules/verification.md)
  §9 and §10.
- `excluded_actions` — packet `authority`, optional: named actions this
  item's executor may not take without suspending through the ticket's
  `## Handoff`. Never a path in this item's own `write_scope`: an item
  forbidden to touch what it is granted cannot be executed as written,
  and the contradiction is the cut's to fix, not the executor's.
- `isolation` — packet `authority`, optional: `required` | `none` —
  whether this item executes in a workspace of its own; absent reads
  `none`. The decomposer is the field's only setter. The declaration
  `scripts/workspace.py check` grades and `scripts/tickets.py packet`
  conditions on; the join runs that check before the merge, because
  afterwards the item's tip is already an ancestor of the run tip and a
  stamped item exits clean by design.
- `bound` — packet `bounds`: the item's effort budget.
- `claimed_by`, `claimed_at` — lifecycle: set on claim. A claim is stale
  when no write to the ticket's own sections, or to an artifact its
  `## Result` names, has landed for longer than the bound read as a
  duration — 60 minutes when the bound is not one; staleness never rests
  on wall clock alone.
- `workspace_branch`, `workspace_baseline` — lifecycle, optional:
  written by `scripts/workspace.py start` — the branch of the workspace
  the item was executed in, and the revision that workspace derives
  from plus what was dirty at start. Script-written bookkeeping of the
  same class as `claimed_by` / `claimed_at`, so setting them is not the
  executor writing outside its body sections.
- `profile` — packet `profile`, optional: an explicit role override per
  rules/roles.md §4; absent, role resolves from the executor's declared
  role.

## Body sections

In order — completion test plus the packet's remaining parts:

- `## Objective` — packet `objective`: one observable end state, never
  activities.
- `## Fixed inputs` — packet `inputs`: evidence by identity, never prose
  copies and never an unpinned coordinate, which
  [docs/vocabulary.md](../docs/vocabulary.md)'s `identity` entry
  excludes. An item carries verbatim every field its executor's Require
  names.
- `## Completion test` — enumerated criteria, each naming its oracle and
  oracle_class per [verdict.md](verdict.md), and optionally its oracle
  provenance — `pre-existing` (the oracle exists or is concretely
  specified before the unit's work) or `authored-here` (the executing
  context creates it); absent reads `authored-here`. Independence law:
  [rules/verification.md](../rules/verification.md) §10.
- `## Return fields` — packet `return_contract`: the named fields the
  executor's result must carry. A `status` in this list is the result
  envelope's ([result.md](result.md)), never the ticket frontmatter key
  above.
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

## Dispatch

The six packet parts every dispatch carries are the ticket's own fields:
`objective` = `## Objective`, `inputs` = `## Fixed inputs`, `authority` =
`write_scope` plus `excluded_actions`, `bounds` = `bound`,
`return_contract` = `## Return fields`, and `reply_to`, which the
dispatcher supplies at packet time and the child never infers. A
work-item dispatch supplies the parts by reference to the ticket path. A
packet says what to do; only `inputs` says what is true.

- `inputs` — the child gathers nothing outside them unless the objective
  is itself investigation. The root ticket's binding constraints ride a
  child's `## Fixed inputs` verbatim — never re-derived or summarized.
- `authority` — user interaction is excluded from every child by
  default, per [rules/delegation.md](../rules/delegation.md) §2 (user
  interaction is glue); a packet grants it explicitly to lift the
  exclusion. Hitting an excluded action never runs silently: a work-item
  dispatch suspends through the ticket's `## Handoff`; a packet-only
  child stops and returns partial results plus the exclusion hit, per
  [rules/composition.md](../rules/composition.md) rule 8 — the caller
  re-dispatches with a ticket when resume matters.
- `bounds` — the budget covers reading the `inputs` the packet names,
  stated in whichever currency binds first — for a child handed an
  evidence set, context before tool calls.
- `return_contract` — a dispatch granting a non-empty `write_scope`
  contracts for `changed_artifacts` among the named fields, and a result
  whose changed_artifacts exceed the granted scope is rejected at the
  join regardless of its verdicts. A packet naming no durable artifact
  contracts for a message-only return; nothing else crosses back.
- `reply_to` — the literal identifier the child's closing message must
  address, computed once from the dispatcher's own identity: its own
  assigned name where the dispatcher is itself a named child, `main`
  where it is the top-level orchestrator. Nothing in a child's own
  context reveals who dispatched it, and a spawn surface whose return
  travels only by an addressed message turns a missing `reply_to` into a
  silently misdirected return, not a loud refusal.
- `profile` — a seventh, optional part: an explicit role override per
  rules/roles.md §4, binding only the dispatch naming it and never
  propagating to a descendant dispatch. Only a missing part among the
  six refuses a dispatch; a missing `profile` never does.

A packet-only dispatch is a ticket the dispatcher does not persist: the
same parts, no file — so no `## Handoff` to suspend through and no
durable record to resume from.

Blame rule, recorded at every join: work the child had to do because a
packet field was missing or false is the caller's defect, delivered or
not; failure to deliver the return contract inside authority and bounds
is the child's. The blame class routes the finding to its causal owner.

A child never re-dispatches its primary work; star topology, attenuation
and the single join are
[rules/delegation.md](../rules/delegation.md) §3–§5.

## Root ticket

A ticket whose `executor` is `orch-decompose` and whose `pack` is stamped
is the run's frozen statement — the input to decomposition, and what
`orch-spec` alone writes. Every other reader, `orch-decompose` included
while cutting, treats it as frozen. It carries the frozen statement in
the fields above:

| the frozen statement | the root ticket's field |
|---|---|
| objective | `## Objective` |
| acceptance | `## Completion test` |
| evidence, exemplars | `## Fixed inputs` — by identity, exemplars by pointer plus each property the imitation must carry |
| affected surfaces | `write_scope`, from which disjoint child scopes are cut |
| binding constraints | `excluded_actions`, and `## Fixed inputs` for what every child inherits verbatim |
| bound | `bound` |

The stamped pack's `required_spec_fields` are entries of its
`## Fixed inputs`. A criterion no oracle can check is a spec defect, not
the decomposer's slack.

Its subtree is `<id>.NN` unit tickets plus the gate stubs
`<id>.gate.critique.<lens>` (read-only, one per stamped lens, in
parallel), `<id>.gate.repair` (write authority over the run scope,
depending on every critique) and `<id>.gate.verify` (depending on repair,
carrying the root's acceptance). The root ticket completes when
`<id>.gate.verify` completes; a successor depends on the root id alone.

A `plan_gate` is the root ticket suspending through its `## Handoff`
after the cut, resumed on approval. Discovered scope is a ticket that
`depends_on` the root's gate — never merged into the running set.

## Template and stub

A composition is a template: a directory of ticket stubs, canonical at
`compositions/<name>/`, instantiated into one run's ticket directory.

- `template.md` — the manifest: frontmatter `name`, `description`,
  `entry` (`routed` | `named`) and `placeholders`, naming every
  `{{placeholder}}` the stubs use; then the prose stating the chain and
  what instantiation must supply.
- Every other `*.md` in the directory is a stub: a ticket per this
  contract missing only `run`, `status` and `claimed_*`, with a
  `{{placeholder}}` wherever instantiation fills a value. A stub's `id`
  is its file stem; its `depends_on` names sibling stems.
- Exactly one terminal stub — the one no other stub depends on. Its
  `## Completion test` is the template's done check; the graph is
  acyclic.
- `tickets.py instantiate <template> --run <run> --set k=v` writes one
  ticket per stub into the run's ticket directory, substituting every
  placeholder and adding the lifecycle keys. An unfilled placeholder is
  refused, and instantiation is all or none: a half-instantiated
  template is a run with a broken graph.

## Executor form

`executor` names a skill in the tree, or `script:<repo-relative path>`
naming a tested script — the ladder's floor as a graph node, so a
deterministic step is a ticket like any other and costs no agent. In a
stub either form may be a `{{placeholder}}`, left to instantiation, which
refuses an unfilled one and so checks the filled value.

Rules: uncovered remainder belongs to the run's queued scope, never to a
ticket; a ticket never widens its own scope or bound; domains extend the
sections, never replace them.
