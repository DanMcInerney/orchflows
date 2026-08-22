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
- `admission` — lifecycle: v1 tickets start `v1:pending`; successful
  admission replaces it with the portable `v1:<adapter>:sha256:<digest>`
  receipt for the exact cut/cohort snapshot. Only the common admission
  grader may move `pending` to `ready` or atomically claim it.
- `cohort` — graph position: `v1:ticket:<id>`, `v1:root:<root>`, or
  `v1:batch:<digest>`. Admission grades all members together and seals the
  cohort when one member becomes live; amendment invalidates every unsealed
  member's receipt.
- `root_generation` — v2 lifecycle: the content identity
  `v2:root:<root-id>:<ordinal>:sha256:<digest>` of the canonical frozen root assignment fields.
  Its digest excludes cut membership, lifecycle
  bookkeeping, and executor-owned sections.
- `cut_generation` — v2 lifecycle and graph position: the content identity
  `v2:cut:<root-id>:<ordinal>:sha256:<digest>` of one complete validated cut.
  Its digest covers the referenced root generation, unit and gate assignment digests,
  coverage-map digest, ownership-region declarations, and
  merge-oracle identities. It excludes lifecycle bookkeeping, executor-owned
  sections, and self-referential generation fields.
- `ownership_regions` — v2 packet `authority`: a list of canonical records
  shaped as
  `{"artifact":"<path>","merge_oracle":"<identity>","owner":"<ticket-id>","selector":{"kind":"<kind>","value":"<stable identity>"}}`.
  Selector kind is exactly `symbol`, `heading`, `json-pointer`, or
  `adapter-equivalent`. Same-artifact parallelism requires the stamped
  adapter to prove stable non-overlap at the pinned identity and binds a
  merge oracle. A `line-number` identity and string inequality as proof are
  prohibited; the fallback is dependency-order work or one sole owner.
- `assignment_seal` — v2 lifecycle: `sha256:<digest>` of the canonical bytes
  of the exact validated assignment fields `objective`, `inputs`, `authority`,
  `dependencies`, `acceptance`, and `executor`. The exact validated assignment digest
  is sealed before worker ready, claim, or packet emission. A post-seal assignment change
  creates a new generation.
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
- `mutations` — v1 Git/design cut plan: a list of `create:<file>`,
  `change:<file>`, `delete:<file>`, or `write:<prefix>/` nodes. Paths are
  repository-relative POSIX paths without globs; each node fits
  `write_scope`. Scope-edge closure may assign a required companion to one
  dependency-ordered cohort member but never widens authority.
- `excluded_actions` — packet `authority`, optional: named actions this
  item's executor may not take without suspending through the ticket's
  `## Handoff`. Never a path in this item's own `write_scope`: that
  contradiction is the cut's to fix, not the executor's.
- `isolation` — packet `authority`, optional: `required` | `none` —
  whether this item executes in a workspace of its own; absent reads
  `none`. The decomposer is the field's only setter. The declaration
  `scripts/workspace.py check` grades and `scripts/tickets.py packet`
  conditions on; the join runs that check before assembly. Executor-specific
  isolation and commit procedure belongs to that executor's skill; the field
  here is only its generic authority shape.
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
  verbatim every field its executor's Require names. Every non-empty bullet
  is one recursively key-sorted canonical UTF-8 JSON record with no
  insignificant whitespace, exactly one of:

  `- input: {"identity":{...},"name":"baseline","type":"identity"}`

  `- input: {"name":"question","type":"literal","value":"exact value"}`

  Names are unique lower-kebab. Literals carry exact JSON parameters;
  identities resolve through the stable adapter selected by the stamped
  pack. Objective states the routed observable end state; procedure belongs
  to the executor, never to inputs.
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
  above. It may contain at most one exact size line:

  `return-size: {"counter":"words-v1","maximum":3000,"minimum-complete":"return-fixture","target":"result"}`

  The counter is `words-v1` or `lines-v1`; maximum is positive and the named
  fixed input is one resolving minimum-complete text fixture. No second
  numeric word/line constraint is allowed. [Result](result.md) alone owns
  actual-return identity resolution, counting, and completion enforcement
  for this clause.
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

For v2, `## Result`, `## Verification`, `## Feedback`, `## Risks`, and
`## Handoff` are append-only executor-owned sections. They never enter a
root generation, cut generation, or assignment seal digest.

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

## Admission and migration

All producers issue v1 tickets as pending. `ready` and `claim` call the same
portable grader and compare-and-swap the same exact snapshot; packet emission
requires a live claim and current receipt. Pending/ready v0 tickets and stale
v0 reclaims are re-cut into v1. Already-live v0 claims alone dispatch as
`legacy-unadmitted`; claimed/terminal history and friction records are never
rewritten. Direct status writes cannot create `ready` or `claimed`.

The absence of all four v2 fields — `root_generation`, `cut_generation`,
`ownership_regions`, and `assignment_seal` — means v1, and no v1 value is reinterpreted.
History for every claimed or terminal v1 ticket is never rewritten and keeps
its original execution and history. A pending or ready v1 ticket stays v1
unless the caller explicitly recuts or migrates it. A live v1 root continues
through a successor or new v2 root that cites its Handoff or Result identity.
New producers may opt into v2 explicitly while legacy and ad-hoc producers
remain v1 during migration; existing v0 behavior remains unchanged.

## T0 supersession

A named-field or enum change to this contract or
[pack-signature.md](pack-signature.md) lands as an explicit T0 supersession.
The change updates its focused contract checks and re-pins the superseded
canonical bytes in `tests/pins.json`; it never reinterprets claimed or
terminal history.

This T0 supersession adds only verify-gate mutation-plan carriage. Every
`<id>.gate.verify` `## Fixed inputs` carries `mutation-plan-paths`, whose
value is shaped as
`{"identity":"sha256:<64 lowercase hex>","paths":["<path>"]}`. The paths are
the sorted unique repository-relative POSIX paths derived from the admitted
root `mutations`; their canonical UTF-8 JSON array is bound by SHA-256, and
the identity is `sha256:<64 lowercase hex>`. A
malformed mutation refuses gate creation rather than omitting an entry. This
does not change approved v2 lifecycle fields or semantics, v1 interpretation
or history, or v0 migration behavior.

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
The root carries `independence: gate`. Its `checked_by` records only the cut
reader below; it never satisfies the root result's outside-independence path,
which is the composite gate.

A root's cut is checked (rules/verification.md §10) before its first
unit is promoted: `scripts/cutcheck.py` over the issued subtree always,
and one fresh reader as well where that subtree holds three or more
`<id>.NN` or that run reported an advisory — correcting it through
`tickets.py amend` and `new` rather than in the run's workspace, which
the units write; `checked_by` on a root records that cut checker.

For a multi-kind request, `orch-spec` persists the ordered successor plan as
`successors.md` at `runs/<run>/successors.md` before opening the first root and is its sole
writer. A completed frontier is the trigger that returns the predecessor's
accepted result identity to that owner; the owner opens the planned successor
root in its own physical run, cites the identity, and advances the plan.

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
