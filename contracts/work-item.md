# Work-item contract (ticket)

A ticket is one sealed semantic assignment plus system-owned lifecycle state.
The generated [lifecycle cells](../docs/lifecycle.md#ticket-lifecycle)
relate this shape to its authorized events without restating them here.

Location: `<state-root>/tickets/<run>/<id>.md`, where
`scripts/state_root.py` resolves the user-scope state sink.

## Semantic assignment

The author-facing payload has exactly these sections, in order:

- `## Goal` — one observable end result. It is not an implementation plan.
  There is no separate done-when or completion-test section.
- `## Context` — relevant facts, prior decisions, and exceptional constraints
  the executor cannot infer from the repository. Write `[]` when none apply.
- `## Suggested files` — optional, non-binding starting points. The executor
  may ignore them and may change or create any files needed to achieve Goal.

The executor chooses implementation, tests, and verification. A test-oriented
executor derives its tests from Goal. Repository-global deterministic gates
still apply at the integrated tip. The assignment carries no authored file
path restrictions, prescribed actions, named checks, or prescribed tests.

## System-owned metadata

Frontmatter is lifecycle and graph state, separate from semantic content:

- `id`, `run`, `status` — stable identity, owning run, and lifecycle state.
- `executor`, optional `sequence`, `profile`, and `pack` — exact dispatch and
  role binding. Callable executors are the seven registered verbs
  `orch-execute`, `orch-check`, `orch-decompose`, `orch-integrate`,
  `orch-frontier`, `orch-loop`, and `orch-spec`; `script:<repo-relative path>`
  is the only other executable form. Skill substitution is not allowed.
- `depends_on` — ticket ids that must complete first.
- `bound` — operational effort bound.
- `independence`, `isolation` — checker/gate and workspace mechanics.
- `review_order` — the sealed zero-based order of a composite-gate lens.
- `review_kind` — optional typed review lane: `critique`, `repair`, or
  `verify`; its value selects the mechanical checker or repair projection.
- `admission`, `root_generation`, `cut_generation`, `assignment_seal` — the
  deterministic generation, validation, seal, and admission records.
- `claimed_by`, `claimed_at`, `checked_by`, `review_stage`, `workspace_path`,
  `workspace_branch`, and `workspace_baseline` — lifecycle observations written
  by their owning tools. `workspace_path` names the pre-dispatch candidate or
  canonical run-scoped evidence store; the Git-only fields fix its branch and
  starting revision.
- `review_stage` names the completed derived `<id>.check` ticket whose
  protocol-owned join authenticates `checked_by`; it is never a caller's
  findings payload.
- `dispatch_v1` — the canonical JSON `orchflows.dispatch.v1` attempt record.
  It is operational state, excluded from the assignment fingerprint.
- `review_v1` — the canonical JSON immutable review-stage ledger. It is
  operational state, excluded from the assignment fingerprint.

`status` is `pending`, `ready`, `claimed`, `suspended`, `complete`, `blocked`,
`stalled`, `failed`, or `limited`. Admission alone creates `ready`; claim alone
creates `claimed`; the join alone records terminal status.

Sealing fingerprints Goal, Context, optional Suggested files, exact executor,
dependencies, and necessary system identity. It never creates file authority
or a prescribed test oracle. Accepted generation identity is immutable;
compare-and-swap sealing refuses a stale snapshot.

## Dispatch-v1 attempt state

The ticket's `dispatch_v1` frontmatter value binds the complete closed
[dispatch contract](dispatch.md). That contract solely owns attempts, records,
packets, receipts, outcomes, joins, precedence, and cutover. Ticket lifecycle
projects its accepted mutations: open creates `claimed`; only the outcome-fenced
join creates `suspended` or a terminal state. Raw status writes cannot mutate a
ticket once its dispatch record exists. A suspended ticket retains claimant
observations for its Handoff, but its joined dispatch attempt is retired.

## Dispatch-v1 packet projection and receipt

Packet projection and receipt are the [dispatch contract](dispatch.md)'s wire
boundary. Reference is the normal projection. Inline seals the whole routing
envelope for an offline receiver and returns the same reserved outcome envelope
for atomic coordinator relay; it never creates a second ticket truth.

## Review-stage ledger

`review_v1` is a closed `orchflows.review.v1` object with an ordered `records`
list. Every record carries its canonical content digest as `identity` and the
exact prior record identity as `predecessor`. `GatePlan` fixes the artifact,
pack, normalized isolation, and ordered lens assignment identities;
`CritiqueAdjudication` fixes complete findings and their accepted subset;
`RepairOutcome` fixes the resulting artifact or proves no-op from an empty
accepted set; `Verification` fixes its artifact, verdict, and evidence.

Composite gate packets copy only the validated predecessor chain. Critique,
repair, and verification joins append their stage atomically with the lifecycle
join. The ordinary distinct checker writes the same `GatePlan` and
`CritiqueAdjudication` carrier before `checked_by`; it must name the fixed
artifact, complete canonical findings, and accepted subset.

## Executor records

After the semantic sections, tickets carry executor-owned `## Result`,
`## Verification`, `## Feedback`, and `## Risks`; `## Handoff` is optional.
They are append-only after seal and are excluded from assignment fingerprints.
The executor files them as work is produced through `tickets.py result` under
[result.md](result.md), naming the packet's `assignment_seal`, `dispatch_id`,
a unique `record_id`, and recorded writer. Reference packet
prompts carry the first three fixed identities and a `RECORD_ID` placeholder;
the executor chooses a fresh record id for each streamed write. At closing,
every executor commits or returns the reserved
[dispatch outcome](dispatch.md#outcome-and-join). `Feedback` and `Risks` use
`[]` when empty. Outcome evidence is a closing delta: it contains only evidence
not already materialized by streamed result records, and every item is appended
exactly once.

## Roots, decomposition, and integration

A root is the ticket named by a `root_generation`. A direct root may bind any
lawful registered executor and owns the whole artifact. A decomposed root binds
`orch-decompose`; every member and gate ticket uses this same semantic shape.

Each physical run has one root identity. Its `root_generation` uses ordinal
`1`; only cut drafts can advance before seal. A semantic change after seal is
not an in-run amendment: after the accepted predecessor result identity
resolves, it opens a successor run whose root `## Context` cites that identity.
The predecessor ticket and run remain historical state and are not rewritten.

Decomposition may suggest files, but it does not grant exclusive predicted
scope and parallel tickets need not predict disjoint paths. Isolated candidates
receive repository/workspace write authority by default. At integration, the
integrator mechanically inspects actual diffs and ordinary Git conflicts,
resolves overlaps, regenerates shared derived artifacts once, and runs the
final deterministic gate. An actual diff differing from Suggested files is
never by itself a rejection.

## Template and executor form

A composition is `template.md` plus ticket stubs. `tickets.py instantiate`
substitutes placeholders, validates one acyclic graph with one terminal, seals
the exact snapshot, and writes all tickets or none.

`executor` names one registered callable verb or `script:<repo-relative path>`.
Optional `sequence` is an ordered chain of stage names declared by the stamped
pack's execute-side `stages` cell; stage names are pack data, not skill
bindings. A sequence is one child, established once at the role resolved from
its callable executor. `orch-execute` resolves the pack's execute cells and
`orch-check` resolves its check cells; neither may import a superseded skill
body or invent a second pack parser. Anything needing a fresh role or
independent verdict is a new ticket and child. Domains may add facts to
Context but do not replace the semantic sections.

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/work-item.md`. Do not edit this section by hand; the validator refuses byte drift.

### `review_state`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | `orchflows.review.v1` |
| `records` | yes | — |

### `review_record_common`

| field | required | declared values |
| --- | --- | --- |
| `identity` | yes | — |
| `kind` | yes | `GatePlan`, `CritiqueAdjudication`, `RepairOutcome`, `Verification` |
| `predecessor` | yes | — |
| `protocol` | yes | — |

### `review_gate_plan`

| field | required | declared values |
| --- | --- | --- |
| `artifact` | yes | — |
| `criteria` | yes | — |
| `isolation` | yes | — |
| `mode` | yes | `gate`, `checker` |
| `pack` | yes | — |
| `root` | yes | — |
| `workspace` | yes | — |

### `review_criterion`

| field | required | declared values |
| --- | --- | --- |
| `identity` | yes | — |
| `lens` | yes | — |
| `order` | yes | — |
| `ticket` | yes | — |

### `review_finding`

| field | required | declared values |
| --- | --- | --- |
| `blocking` | yes | — |
| `class` | yes | — |
| `evidence` | yes | — |
| `goal_impact` | yes | — |
| `id` | yes | — |
| `repair` | yes | — |
| `summary` | yes | — |

### `review_critique`

| field | required | declared values |
| --- | --- | --- |
| `accepted` | yes | — |
| `adjudicated_by` | yes | — |
| `artifact` | yes | — |
| `findings` | yes | — |
| `lens` | yes | — |

### `review_repair`

| field | required | declared values |
| --- | --- | --- |
| `accepted` | yes | — |
| `artifact` | yes | — |
| `by` | yes | — |
| `input_artifact` | yes | — |
| `no_op` | yes | — |
| `result` | yes | — |

### `review_verification`

| field | required | declared values |
| --- | --- | --- |
| `artifact` | yes | — |
| `by` | yes | — |
| `evidence` | yes | — |
| `verdict` | yes | `PASS`, `FAIL`, `UNVERIFIED` |
| `covers` | no | — |

### `ticket_assignment_sections`

| field | required | declared values |
| --- | --- | --- |
| `Goal` | yes | — |
| `Context` | yes | — |
| `Suggested files` | no | — |

### `ticket_frontmatter`

| field | required | declared values |
| --- | --- | --- |
| `id` | yes | — |
| `run` | yes | — |
| `status` | yes | `pending`, `ready`, `claimed`, `suspended`, `complete`, `blocked`, `stalled`, `failed`, `limited` |
| `admission` | no | — |
| `executor` | yes | — |
| `sequence` | no | — |
| `pack` | no | — |
| `profile` | no | — |
| `independence` | no | — |
| `depends_on` | yes | — |
| `isolation` | no | — |
| `bound` | yes | — |
| `claimed_by` | no | — |
| `claimed_at` | no | — |
| `checked_by` | no | — |
| `root_generation` | no | — |
| `cut_generation` | no | — |
| `assignment_seal` | no | — |
| `workspace_branch` | no | — |
| `workspace_baseline` | no | — |
| `workspace_path` | no | — |
| `dispatch_v1` | no | — |
| `review_order` | no | — |
| `review_v1` | no | — |
| `review_stage` | no | — |
| `review_kind` | no | `critique`, `repair`, `verify`, `null` |

<!-- END GENERATED T0 SHAPES -->

## T0 supersession

A named-field change to this contract is an explicit T0 supersession. There is
one current reader and writer: no compatibility aliases, dual parsing, or
migration mode. Historical user state is not rewritten.

T0 supersession record sha256:b2d5d570a37764b9c83f305eaf90a98f604ce98c5d479ecbd7abb1059b9c94aa: executor records now enter through the attributed result writer.

T0 supersession record sha256:1d95dfb82a4489f5d05d067d36fc669720c18424359d8b8c84f0857bde3a53fb: `dispatch_v1` adds the sole atomic execution-attempt and committed-record seam.

T0 supersession record sha256:d12f7cb34c27575e52f78faf4aa5348d1c5ee35f5f14bf9fc502103560435fe5: dispatch-v1 adds committed reference or inline packet projection and deterministic receipt validation.

T0 supersession record sha256:89179c389a091321aca0ed52ef81dd5947041fcbf0a57b52e18136775b33e8b5: executor records now cross the dispatch-v1 committed-record
seam atomically; claim-name-only result filing is removed.

T0 supersession record sha256:e907a499354bc667db48f0cac413a3bf216a86f745ee0aeab0d70a71eced03f8: dispatch-v1
lifecycle operations and joins are fixed-record transitions over one absolute
attempt lease; raw status writes cannot terminate or suspend a v1 attempt.

T0 supersession record sha256:0d3198c3bca64480a60502a7d621be4e6ca6349fc4ef74e9b18f30951fdec956: the
closed dispatch grammar and reserved outcome return moved to `dispatch.md`;
public legacy role-bearing routes are removed.

T0 supersession record sha256:0c37ca5c93bc6f4b5042e8fb746f3fc10a6e82f45228d7889e678be500da0d68:
suspension retains claimant observations after retiring its attempt, and
closing outcome evidence is an unstreamed delta.

T0 supersession record sha256:85860c216a05aab9272033f2a368fde11d232e082f7d3d5cc82931bcf2e8bf36:
`review_order` seals composite-lens order and operational `review_v1` records
the immutable GatePlan through Verification chain.

T0 supersession record sha256:73c86dd421ed6da6acf7893e881a652ffeee2badc3e496e3fb810e4661519804:
workspace establishment is a host-owned pre-dispatch
transition. `workspace.py start` records `workspace_path` for every supported
adapter, plus the existing Git branch/baseline observations, and creates the
canonical run-scoped research evidence store.

T0 supersession record sha256:c6fbeafb3f9daf27e689ae00d80c1bf2a6f9332aca1183e18ecebeee7b2cdb5f:
each run has one semantic root at ordinal 1; a post-seal semantic change opens
a successor run linked to the accepted predecessor result identity instead of
minting an in-run root amendment.

T0 supersession record sha256:3c119a98c0298cd90fa6e7fc3f35c1c77e41750b48a106f631af0a68f589482e:
the callable tier is the seven-verb registry; execute and check consume
resolved pack cells, review lanes use typed `review_kind`, and superseded
skill bindings are rejected rather than aliased.
