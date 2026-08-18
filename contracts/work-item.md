# Work-item contract (ticket)

The one unit of work, plan, and record: a delegation packet made durable
— packet parts ⊕ completion test ⊕ lifecycle ⊕ graph position. Every
decomposition emits work items, every executor consumes exactly one,
every join integrates one. On disk it is a markdown ticket in the local
tracker — the one durable record of its dispatch, which the executor
writes its result into.

Location: `<state-root>/tickets/<run>/<id>.md`, the state root being the
user-scope sink `scripts/state_root.py` resolves — one per user, outside
every repository. One run's tickets have exactly one path, identical from
the orchestrator, from every executor workspace, after any workspace is
removed, and after the repository is removed. A dispatch names it
absolutely; an `excluded_actions` forbidding a directory always carves out
the run's own directory in the sink, since the executor writes its Result
there.

Frontmatter, mapped to packet parts, lifecycle, and graph position:

- `id` — lifecycle: unique within the run; stable once issued.
- `run` — lifecycle: the owning run id.
- `status`: `pending` | `ready` | `claimed` | `suspended` | `complete` |
  `blocked` | `stalled` | `failed` | `limited` — lifecycle; transitions
  per `orch-frontier`. `pending` and `suspended` are the two non-terminal
  waits; a suspended ticket stays claimed, resumable from its
  `## Handoff`. `complete` requires PASS on every required criterion;
  nothing else does. Terminal status — `complete`, `blocked`, `stalled`,
  `limited`, `failed` — is set only by the join (`orch-integrate`), never
  by the executor, and is the set [worklog.md](worklog.md)'s `terminal`
  and [result.md](result.md)'s `status` are read in.
- `executor` — graph position: the named skill or script bound to do the
  work, per Executor form below; from the pack's executor cell, its
  assembly cell for the terminal item, or the orchestrator directly for
  an ad-hoc ticket.
- `pack` — optional: the stamped pack whose cells bind this item's
  workspace, oracles, and craft; set by decomposition from the root
  ticket's stamp, or by the ad-hoc cutter when a pack fits. Absent, no
  cell binding applies and workspace semantics are plain artifact paths.
- `independence` — optional: `gate` | `checker` — the
  [rules/verification.md](../rules/verification.md) §10 source this
  item's `authored-here` acceptance rides. For authored-here acceptance,
  exactly one outside-independence path is selected: `gate` is set at cut time when the downstream gate
  re-verifies all authored-here criteria on this item, regardless of oracle
  class; otherwise `checker`, which an absent field reads as.
- `checked_by` — optional, lifecycle: the single immutable identity set by
  the §10 checker on its pass, through `tickets.py check`. It is invalid on
  a non-root ticket whose `independence` is `gate`; root cut bookkeeping is
  defined under Root ticket.
- `depends_on` — graph position: list of item ids; empty list when none.
- `write_scope` — packet `authority`: exactly what this item may change,
  in the workspace semantics of the ticket's `pack`; a strict subset of
  the run's scope. The ticket file's own result sections and `status` are
  ticket bookkeeping, not workspace content, and sit outside
  `write_scope`: the executor writes only `## Result`, `## Verification`,
  `## Feedback`, `## Risks`, and — when suspending — `## Handoff`. A §10
  checker corrects inside this same `write_scope`, per
  [rules/verification.md](../rules/verification.md) §9 and §10 — on a
  root ticket, the cut instead (Root ticket).
- `excluded_actions` — packet `authority`, optional: named actions this
  item's executor may not take without suspending through the ticket's
  `## Handoff`. Never a path in this item's own `write_scope`: that
  contradiction is the cut's to fix, not the executor's.
- `isolation` — packet `authority`, optional: `required` | `none` —
  whether this item executes in a workspace of its own; absent reads
  `none`. The decomposer is the field's only setter. The declaration
  `scripts/workspace.py check` grades and `scripts/tickets.py packet`
  conditions on; the join runs that check before the merge.
- `bound` — packet `bounds`: the item's effort budget.
- `claimed_by`, `claimed_at` — lifecycle: set on claim. A claim is stale
  when no write to the ticket's own sections, or to an artifact its
  `## Result` names, has landed for longer than the bound read as a
  duration — 60 minutes when the bound is not one; staleness never rests
  on wall clock alone.
- `workspace_branch`, `workspace_baseline` — lifecycle, optional:
  written by `scripts/workspace.py start` — the branch of the workspace
  the item was executed in, and the revision that workspace derives from
  plus what was dirty at start. Script-written bookkeeping of the
  `claimed_*` class, so setting them is not the executor writing outside
  its body sections.
- `profile` — packet `profile`, optional: an explicit role override per
  rules/roles.md §4; absent, role resolves from the executor's declared
  role.
- `plan_gate` — optional, root ticket only: `true` suspends the root
  through its `## Handoff` after the cut, parking the frontier.

Body sections, in order — completion test plus the packet's remaining
parts:

- `## Objective` — packet `objective`: one observable end state, never
  activities.
- `## Fixed inputs` — packet `inputs`: evidence by identity, never prose
  copies and never an unpinned coordinate, which the `identity` entry of
  [docs/vocabulary.md](../docs/vocabulary.md) excludes. An item carries
  verbatim every field its executor's Require names.
- `## Completion test` — enumerated criteria, each naming its oracle and
  oracle_class per [verdict.md](verdict.md), and optionally its oracle
  provenance — `pre-existing` (the oracle exists or is concretely
  specified before the unit's work) or `authored-here` (the executing
  context creates it); absent reads `authored-here`. Independence law:
  [rules/verification.md](../rules/verification.md) §10. An executor
  closes its item by running this test through `orch-verify` at the
  result's fixed identity, over every identity the criteria cover.
- `## Return fields` — packet `return_contract`: the named fields the
  executor's result must carry. A `status` in this list is the result
  envelope's ([result.md](result.md)), never the ticket frontmatter key
  above.
- `## Result` — the filing law: the executor's, written as produced —
  what changed, by identity, cited here or in the store the packet
  names, per rules/delegation.md §10. A §10 checker appends its own pass — findings,
  changes, invalidated entries — and never rewrites the executor's.
- `## Verification` — verdict entries, one per criterion.
- `## Feedback` — bounded observations; `[]` when none.
- `## Risks` — `[]` when none.
- `## Handoff` — optional: the suspension, resumption, or escalation
  record — the reason (the excluded action hit, or why a larger topology
  is needed), remaining scope and known gaps, and budget state per bound.
  A handoff is complete when a fresh agent can resume from it without
  reading the suspended agent's transcript; compact to identities and
  verdicts, redacting transcript prose. A second suspension or escalation
  past [rules/delegation.md](../rules/delegation.md) §9's once-per-dispatch
  bound is a terminal `blocked`. On resumption, accepted evidence stays
  accepted — re-verify only entries the handoff marks unverified or
  invalidated.

## Dispatch

The six packet parts every dispatch carries are the ticket's own fields:
`objective` = `## Objective`, `inputs` = `## Fixed inputs`, `authority` =
`write_scope` plus `excluded_actions`, `bounds` = `bound`,
`return_contract` = `## Return fields`, and `reply_to`, which the
dispatcher supplies at packet time and the child never infers. `profile`
is a seventh, optional part (rules/roles.md §4–§5); only a missing part
among the six refuses a dispatch. A work-item dispatch supplies the parts
by reference to the ticket path. A packet says what to do; only `inputs`
says what is true.

- `inputs` — the child gathers nothing outside them unless the objective
  is itself investigation. The root ticket's binding constraints ride a
  child's `## Fixed inputs` verbatim — never re-derived or summarized.
- `authority` — what a child may not do unless the packet grants it, and
  what hitting an excluded action does, are
  [rules/delegation.md](../rules/delegation.md) §2 and §9 and
  [rules/composition.md](../rules/composition.md) rule 8.
- `bounds` — the budget covers reading the `inputs` the packet names,
  stated in whichever currency binds first — for a child handed an
  evidence set, context before tool calls.
- `return_contract` — a dispatch granting a non-empty `write_scope`
  contracts for `changed_artifacts` among the named fields, and a result
  whose changed_artifacts exceed the granted scope is rejected at the
  join regardless of its verdicts. Where the packet names none,
  [rules/delegation.md](../rules/delegation.md) §10 fixes the return.
- `reply_to` — the literal identifier the child's closing message must
  address, computed once from the dispatcher's own identity: its own
  assigned name where the dispatcher is itself a named child, `main`
  where it is the top-level orchestrator.

Blame rule, recorded at every join and routing the finding to its causal
owner: work the child had to do because a packet field was missing or
false is the caller's defect, delivered or not; failure to deliver the
return contract inside authority and bounds is the child's.

## Root ticket

A ticket whose `executor` is `orch-decompose` and whose `pack` is stamped
carries the run's frozen statement, whose one editor is
[docs/vocabulary.md](../docs/vocabulary.md)'s `spec` entry, in the fields
above:

objective → `## Objective`; acceptance → `## Completion test`; evidence
and exemplars → `## Fixed inputs`, by identity, exemplars by pointer plus
each property the imitation must carry; affected surfaces →
`write_scope`, from which disjoint child scopes are cut; binding
constraints → `excluded_actions` plus the `## Fixed inputs` every child
inherits verbatim; bound → `bound`. The stamped pack's
`required_spec_fields` are entries of that `## Fixed inputs`, and a
criterion no oracle can check is a spec defect, not the decomposer's
slack.

A decomposed physical run has one root ticket and one composite gate. Its
subtree is `<id>.NN` unit tickets plus the gate stubs
`<id>.gate.critique.<lens>` (read-only, one per unique lens name, in
parallel), `<id>.gate.repair` (the gate's one repair, with write authority
over the run scope and behind every critique) and `<id>.gate.verify` (the
gate's one verification, behind repair and carrying the root's acceptance);
a loop ticket's iterations are `<id>.iter.NN`.
Completion and succession are that vocabulary's `root ticket` entry, and
discovered scope is a ticket that `depends_on` the run's gate.

A root's cut is checked (rules/verification.md §10) before its first
unit is promoted: `scripts/cutcheck.py` over the issued subtree always,
and one fresh reader as well where that subtree holds three or more
`<id>.NN` or that run reported an advisory — correcting it through
`tickets.py amend` and `new` rather than in the run's workspace, which
the units write; `checked_by` on a root records that cut checker.

## Template and stub

A composition is a template: a directory of ticket stubs plus the
manifest `template.md`, canonical at `compositions/<name>/`, which
`tickets.py instantiate <template> --run <run> --set k=v` writes into one
run's ticket directory, all or none. What a stub is — its keys, its
sections, its `id` and `depends_on` edges, the single terminal stub, the
acyclic graph, every `{{placeholder}}` instantiation must fill, and every
refusal it raises — is `scripts/tickets.py`'s `template_defects`, which
grades each stub in its own words; the manifest is `tools/validate.py`'s.
A template run's bound is the sum of its stubs' `bound`s.

## Executor form

`executor` names a skill in the tree, or `script:<repo-relative path>`
naming a tested script — the ladder's floor as a graph node, so a
deterministic step is a ticket like any other and costs no agent.

Rules: uncovered remainder belongs to the run's queued scope, never to a
ticket; a ticket never widens its own scope or bound; domains extend the
sections, never replace them.
