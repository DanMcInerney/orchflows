# Work-item contract (ticket)

The one unit of work, plan, and record — a delegation packet made durable:
packet parts ⊕ completion test ⊕ lifecycle ⊕ graph position.

Location: `<state-root>/tickets/<run>/<id>.md`, the state root being the
user-scope sink `scripts/state_root.py` resolves. An `excluded_actions`
forbidding a directory always carves out the run's own directory there.

Frontmatter, mapped to packet parts, lifecycle, and graph position:

- `id` — lifecycle: unique within the run; stable once issued.
- `run` — lifecycle: the owning run id.
- `admission` — lifecycle: `v1:pending` at issue, then the portable
  `v1:<adapter>:sha256:<digest>` receipt for the exact cut/cohort snapshot.
  `scripts/tickets_lifecycle.py` owns the grade-then-swap protocol both
  `ready` and `claim` run; direct status writes create neither state.
- `cohort` — v1 graph position and v1's alone: `v1:ticket:<id>`, `v1:root:<root>`,
  or `v1:batch:<digest>`, graded and sealed as one when a member goes live;
  amendment invalidates every unsealed member's receipt. A v2 ticket carries none.
- `root_generation`, `cut_generation`, `ownership_regions`,
  `assignment_seal` — the v2 fields: content identities
  `v2:root:<root-id>:<ordinal>:sha256:<digest>` and
  `v2:cut:<root-id>:<ordinal>:sha256:<digest>`; canonical region records shaped
  `{"artifact":"<path>","merge_oracle":"<identity>","owner":"<ticket-id>","selector":{"kind":"<kind>","value":"<stable identity>"}}`;
  and `sha256:<digest>` over the validated assignment fields `objective`, `inputs`,
  `authority`, `dependencies`, `acceptance`, `executor`. Digests, selectors, seal,
  and the migration under which the absence of all four v2 fields means v1 and no
  v1 value is reinterpreted are [rules/topology.md](../rules/topology.md) §8–§11's.
- `status`: `pending` | `ready` | `claimed` | `suspended` | `complete` |
  `blocked` | `stalled` | `failed` | `limited` — lifecycle, transitions per
  `orch-frontier`: the first four live, `pending` and `suspended` the two
  non-terminal waits and a suspended ticket staying claimed, resumable from its
  `## Handoff`; the last five terminal, the join's (`orch-integrate`) alone and
  the set [worklog.md](worklog.md)'s `terminal` and [result.md](result.md)'s
  `status` read in, `complete` requiring PASS on every required criterion.
- `executor` — graph position: the named skill or script bound to do the
  work, per Executor form below; the pack's executor cell, its assembly cell
  for the terminal item, or the orchestrator selects it.
- `pack` — optional: the stamped pack binding this item's workspace, oracles,
  and craft — set by decomposition from the root ticket's stamp, or by the
  ad-hoc cutter when a pack fits. Absent, workspace semantics are plain paths.
- `independence` — optional: `gate` | `checker` — which
  [rules/verification.md](../rules/verification.md) §10 source this item's
  `authored-here` acceptance rides, exactly one outside-independence path
  being selected: `gate`, the downstream gate re-verifying all authored-here
  criteria regardless of oracle class, or `checker`, an absent field's read.
- `checked_by` — optional, lifecycle: the single immutable identity the §10
  checker sets through `tickets.py check`. Invalid on a non-root ticket
  whose `independence` is `gate`; a root's is under Root ticket.
- `depends_on` — graph position: list of item ids; empty list when none.
- `write_scope` — packet `authority`: exactly what this item may change, in
  the workspace semantics of the ticket's `pack`; a strict subset of the
  run's scope. Outside it sit the ticket's own `status` and its
  executor-owned sections — `## Result`, `## Verification`, `## Feedback`,
  `## Risks`, `## Carry`, and, suspending, `## Handoff` — append-only under
  v2 and never in a generation or seal digest. A §10 checker corrects inside
  this same `write_scope` ([rules/verification.md](../rules/verification.md)
  §9); a root's cut instead.
- `mutations` — v1 Git/design cut plan: `create:<file>`, `change:<file>`,
  `delete:<file>`, or `write:<prefix>/` nodes, each a repository-relative
  POSIX path without globs that fits `write_scope`.
- `excluded_actions` — packet `authority`, optional: named actions this
  item's executor may not take without suspending through `## Handoff`, never
  a path in its own `write_scope` — that contradiction is the cut's to fix.
- `isolation` — packet `authority`, optional: `required` | `none` — whether
  this item executes in a workspace of its own; absent reads `none`. The
  decomposer is the field's only setter, `scripts/workspace.py check` grades
  the declaration, and the join runs that check before assembly.
- `bound` — packet `bounds`: the item's effort budget.
- `claimed_by`, `claimed_at` — lifecycle: set on claim; when a claim goes
  stale is `scripts/tickets_bound.py`'s.
- `workspace_branch`, `workspace_baseline` — lifecycle, optional: the
  workspace's branch and the revision it derives from, written by
  `scripts/workspace.py start` — script bookkeeping of the `claimed_*` class.
- `profile` — packet `profile`, optional: an explicit role override per
  rules/roles.md §4; absent, role resolves from the executor's declared role.
- `plan_gate` — optional, root ticket only: `true` suspends the root through
  its `## Handoff` after the cut, parking the frontier.

Body sections, in order — completion test plus the packet's remaining parts:

- `## Objective` — packet `objective`: one observable end state, never activities.
- `## Fixed inputs` — packet `inputs`: evidence by identity, never prose
  copies and never an unpinned coordinate, which the `identity` entry of
  [docs/vocabulary.md](../docs/vocabulary.md) excludes; procedure belongs to
  the executor, never to inputs. An item carries verbatim every field its
  executor's Require names, each non-empty bullet one recursively key-sorted
  canonical UTF-8 JSON record under a unique lower-kebab name, exactly one of:

  `- input: {"identity":{...},"name":"baseline","type":"identity"}`

  `- input: {"name":"question","type":"literal","value":"exact value"}`

- `## Completion test` — enumerated criteria, each naming its oracle and
  oracle_class per [verdict.md](verdict.md), and optionally its oracle
  provenance — `pre-existing` where the oracle exists or is concretely
  specified before the unit's work, else `authored-here`, which the
  executing context creates and an absent field reads as. Independence law:
  [rules/verification.md](../rules/verification.md) §10. An executor closes
  its item by running each criterion's oracle once at the result's fixed
  identity and recording the entries; its own entries are UNVERIFIED alone,
  the one outside execution arrives per §10, and a later reader reuses an
  entry whose covers are unchanged ([verdict.md](verdict.md)'s invalidation
  clause) rather than re-running it.
- `## Return fields` — packet `return_contract`: the named fields the
  executor's result must carry. A `status` here is the result envelope's
  ([result.md](result.md)), never the ticket frontmatter key above. It may
  carry at most one exact size line, whose resolution, counting, and
  enforcement are [Result](result.md)'s:

  `return-size: {"counter":"words-v1","maximum":3000,"minimum-complete":"return-fixture","target":"result"}`

- `## Result` — the filing law ([rules/delegation.md](../rules/delegation.md)
  §10): the executor's, written as produced — what changed, by identity. A
  §10 checker appends its own pass and never rewrites the executor's.
- `## Verification` — verdict entries, one per criterion; `## Feedback` and
  `## Risks` — bounded observations and risks, `[]` filling either when empty.
- `## Carry` — optional, filed by the executor at close: the conclusions a
  successor needs — decisions, landed identities, hazards, the command to
  re-take a measurement — inlined by `packet` into each dependent's dispatch.
  A successor-facing digest, never transcript: growing with history is wrong.
- `## Handoff` — optional: the suspension, resumption, or escalation record —
  reason, remaining scope and known gaps, budget state — complete when a fresh
  agent can resume from it without the suspended agent's transcript, under
  [rules/delegation.md](../rules/delegation.md) §9's once-per-dispatch bound;
  on resumption accepted evidence stays accepted.

## Dispatch

The six packet parts every dispatch carries are the ticket's own fields:
`objective` = `## Objective`, `inputs` = `## Fixed inputs`, `authority` =
`write_scope` plus `excluded_actions`, `bounds` = `bound`,
`return_contract` = `## Return fields`, and `reply_to` — the literal
identifier the child's closing message addresses, supplied at packet time
and never inferred: the dispatcher's own assigned name, or `main` at the
top level. `profile` is a seventh, optional part (rules/roles.md §4–§5);
only a missing part among the six refuses a dispatch. A packet says what to
do; only `inputs` says what is true. What each part then obliges is
[rules/delegation.md](../rules/delegation.md) §4, §5, §9 and §10 with
[rules/composition.md](../rules/composition.md) rule 8.

Blame rule, recorded at every join: work the child had to do because a packet
field was missing or false is the caller's defect, delivered or not; failure to
deliver the return contract inside authority and bounds is the child's.

## T0 supersession

A named-field or enum change to this contract or
[pack-signature.md](pack-signature.md) lands as an explicit T0 supersession.
The change updates its focused contract checks and re-pins the superseded
canonical bytes in `tests/pins.json`; old admission versions retain their
existing meaning and it never reinterprets claimed or terminal history. This
one note governs both T0 shapes.

## Root ticket

A ticket whose `executor` is `orch-decompose` and whose `pack` is stamped
carries the run's frozen statement, whose one editor is
[docs/vocabulary.md](../docs/vocabulary.md)'s `spec` entry: objective,
acceptance, evidence and exemplars by identity with each property an
imitation must carry, affected surfaces from which disjoint child scopes are
cut, binding constraints every child inherits verbatim, bound. The stamped
pack's `required_spec_fields` are entries of that `## Fixed inputs`; a
criterion no oracle can check is a spec defect, not the decomposer's slack.

Its subtree is `<id>.NN` unit tickets plus the gate stubs
`<id>.gate.critique.<lens>`, `<id>.gate.repair`, and `<id>.gate.verify`,
whose composite shape is [rules/topology.md](../rules/topology.md) §5's; a
loop ticket's iterations are `<id>.iter.NN`, discovered scope a ticket that
`depends_on` the run's gate, completion and succession that vocabulary's
`root ticket` entry, and the ordered successor plan `orch-spec`'s. Each
`<id>.gate.verify` carries the root's acceptance and `mutation-plan-paths`,
`{"identity":"sha256:<64 lowercase hex>","paths":["<path>"]}`: the
sorted unique repository-relative POSIX paths of the admitted root
`mutations`, bound by SHA-256 over their canonical UTF-8 JSON array, a
malformed mutation refusing gate creation. The root carries
`independence: gate`, its `checked_by` recording only its cut reader — the
law [rules/verification.md](../rules/verification.md) §10's, when one is
staffed `orch-frontier`'s — which never satisfies the root result's
outside-independence path, the run's one composite gate.

## Template and stub

A composition is a template: a directory of ticket stubs plus the manifest
`template.md`, canonical at `compositions/<name>/`, which
`tickets.py instantiate <template> --run <run> --set k=v` writes into one
run's ticket directory, all or none. What a stub is — keys, sections, `id`
and `depends_on` edges, the single terminal stub, the acyclic graph, every
`{{placeholder}}` instantiation must fill, every refusal it raises — is
`scripts/tickets.py`'s `template_defects`, the manifest `tools/validate.py`'s,
and a template run's bound the sum of its stubs'.

## Executor form

`executor` names a skill in the tree, or `script:<repo-relative path>` naming
a tested script — the ladder's floor as a graph node, so a deterministic step
is a ticket like any other and costs no agent. An optional `sequence` lists
ordered same-role skills, head equal to `executor`: one child executes each in
this one context ([rules/delegation.md](../rules/delegation.md) §4), one witness
whose verdict on its own changes is void (rules/verification.md §11). Uncovered
remainder belongs to the run's queued scope, never to a ticket; a ticket never
widens its own scope or bound; domains extend the sections, never replace them.
