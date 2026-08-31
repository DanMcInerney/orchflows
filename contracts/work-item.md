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
- `## Context` — the evidence behind Goal, cited by identity: the facts, prior
  decisions, and exceptional constraints the executor cannot infer from the
  repository, as pointers rather than inlined copies. A graph member's Context
  names its root ticket path, because verdict-bearing clauses live there and
  nowhere else. Write `[]` when none apply.
- `## Details` — optional and free-form, authored by whoever cuts the ticket
  for this one executor: read-lists, file anchors, prescribed steps, do-nots,
  definition-of-done commands, and what the closing report should cover. A
  planner that investigated may prescribe as hard as its evidence reaches,
  and every prescription carries the evidence that earned it plus its escape
  hatch: deviation is pre-authorized where following Details would break Goal,
  reported with the observation that forced it.

Goal, Context, and Details are one sealed assignment, and Goal is what the
`done` predicate and the join answer to. Repository-global deterministic gates
still apply at the integrated tip.

## System-owned metadata

Frontmatter is lifecycle and graph state, separate from semantic content:

- `id`, `run`, `status` — stable identity, owning run, and lifecycle state.
- `executor`, optional `profile`, and `pack` — exact dispatch and
  role binding. Callable executors are the six registered verbs
  `orch-execute`, `orch-check`, `orch-decompose`, `orch-integrate`,
  `orch-frontier`, and `orch-outline`; `script:<repo-relative path>`
  is the only other executable form. Skill substitution is not allowed, and a
  superseded name is refused naming its successor rather than aliased.
- optional `done` — the canonical JSON done predicate, `{"form", "value"}`:
  form `command`, a deterministic command whose exit 0 is the verdict, or
  form `check`, a criterion no oracle covers, judged by one minted
  `orch-check` ticket. `tickets.py land` is the only evaluator: it runs the
  command in the integrated tree, and that run is the one outside execution
  ([verification.md](../rules/verification.md) §6). A refused command arms
  the next `<id>.repair.NN` round rather than closing the ticket; two rounds
  with no result delta close it `stalled`. A ticket carrying no predicate is
  graded by the driver at the join instead.
- optional `loop` — the canonical JSON loop object making this ticket a loop
  stub. Its `done` is the same binding under the same grammar, read for the
  iteration rather than for the stub. The stub's own `executor` is the
  iteration body's verb. A loop
  stub is never dispatched: `scripts/tickets_loop.py` arms iteration
  `<id>.iter.NN` tickets, evaluates the done-check, and advances — re-arm, or
  terminal `complete` | `limited` | `stalled` — with the worklog as the state
  and `bound` reused as the loop's operational bound.
- `depends_on` — ticket ids that must complete first.
- `bound` — operational effort bound.
- `independence`, `isolation` — checker/gate mechanics, and the rare
  explicit workspace override; an absent `isolation` derives its effective
  value from the stamped pack's adapter (`establishes_isolation`), read
  through one derivation everywhere.
- `review_order` — the sealed zero-based order of a composite-gate lens.
- `review_kind` — optional typed review lane: `critique` or `repair`; its
  value selects the mechanical checker or repair projection. There is no
  standing verification lane: the fresh outside check is the root's own
  `done` predicate, run by land.
- `admission`, `root_generation`, `cut_generation`, `assignment_seal` — the
  deterministic generation, validation, seal, and admission records.
- `checked_by`, `review_stage`,
  `workspace_branch`, and `workspace_baseline` — lifecycle observations written
  by their owning tools. The claim lease — owner and opened time — and the
  established tree both live in the `dispatch_v1` attempt alone; the ticket
  carries no projection of either. `workspace.py establish` is the mechanical owner of the
  candidate an isolated item runs in: it derives, creates, and records that tree
  on the live attempt, and re-establishing it never restamps the baseline. The
  Git-only fields fix that candidate's branch and starting revision.
- `review_stage` names the completed derived `<id>.check` ticket whose
  protocol-owned join authenticates `checked_by`; it is never a caller's
  findings payload.
- `dispatch_v1` — the canonical JSON `orchflows.dispatch.v1` attempt record.
  It is operational state, excluded from the assignment fingerprint.
- `review_v1` — the canonical JSON immutable review-stage ledger. It is
  operational state, excluded from the assignment fingerprint.

`status` is `pending`, `ready`, `claimed`, `suspended`, `complete`, `blocked`,
`stalled`, `failed`, or `limited`. Admission alone creates `ready`; claim alone
creates `claimed`; the join alone records terminal status, off the ticket's
evaluated `done` predicate or the driver's own grade — never off a
disposition the executor claimed for itself.

Sealing fingerprints Goal, Context, optional Details, exact executor,
dependencies, and necessary system identity. Accepted generation identity is
immutable; compare-and-swap sealing refuses a stale snapshot.

## Dispatch-v1 attempt state

The ticket's `dispatch_v1` frontmatter value binds the complete closed
[dispatch contract](dispatch.md). That contract solely owns attempts, records,
launches, outcomes, joins, precedence, and cutover. Ticket lifecycle
projects its accepted mutations: open creates `claimed`; once a dispatch record
exists, only the outcome-fenced join creates `suspended` or a terminal state,
and raw status writes are refused as `dispatch-join-required`. Before any
dispatch record exists, `set-status` is the caller's only route to `suspended`
or a terminal state — it is the pre-dispatch surface, not a legacy one — and
`ready` and `claimed` remain the admission boundary's alone. A suspended ticket
retains claimant observations for whoever resumes it, but its joined dispatch
attempt is retired.

## Dispatch-v1 launch

The [dispatch contract](dispatch.md) owns the launch and its generated prompt.
This ticket is the assignment that prompt points at, and nothing copies it, so
there is no second ticket truth.

## Review-stage ledger

`review_v1` is a closed `orchflows.review.v1` object with an ordered `records`
list. Every record carries its canonical content digest as `identity` and the
exact prior record identity as `predecessor`. `GatePlan` fixes the artifact,
pack, normalized isolation, and ordered lens assignment identities;
`CritiqueAdjudication` fixes complete findings and their accepted subset;
`RepairOutcome` fixes the resulting artifact or proves no-op from an empty
accepted set, and closes the chain.

A composite gate lane consumes only the validated predecessor chain. Critique
and repair joins append their stage atomically with the lifecycle
join. The ordinary distinct checker writes the same `GatePlan` and
`CritiqueAdjudication` carrier before `checked_by`; it must name the fixed
artifact, complete canonical findings, and accepted subset. Those two arrays
are the findings' one durable home: they reach the join as files, never as
prose a consumer would have to read out of a report.

## Executor records

After the semantic sections, a ticket carries one executor-owned `## Report`.
It is append-only after seal and is excluded from assignment fingerprints, and
its form is the executor's: the protocol reads nothing out of it, so it
prescribes no headings inside it. The executor files as work is produced
through `tickets.py result` under
[result.md](result.md), naming the attempt's `assignment_seal`, `dispatch_id`,
a unique `record_id`, and recorded writer. The launch prompt carries the first
three fixed identities and a `RECORD_ID` placeholder;
the executor chooses a fresh record id for each streamed write. At closing,
every executor commits or returns the reserved
[dispatch outcome](dispatch.md#outcome-and-join), whose evidence is one closing
note appended here like any other filing. `land` appends its `done` predicate's
reading to the same section, attributed to the driver that ran it.

## Roots, decomposition, and integration

A root is the ticket named by a `root_generation`. A direct root may bind any
lawful registered executor and owns the whole artifact. A decomposed root binds
`orch-decompose`; every member and gate ticket uses this same semantic shape.

Each physical run has one root identity. Its `root_generation` uses ordinal
`1`; only cut drafts can advance before seal. A semantic change after seal is
not an in-run amendment: after the accepted predecessor result identity
resolves, it opens a successor run whose root `## Context` cites that identity.
The predecessor ticket and run remain historical state and are not rewritten.

Details may name files, but naming them grants no exclusive scope and parallel
tickets need not predict disjoint paths. Isolated candidates receive
repository/workspace write authority by default. At integration, the
integrator mechanically inspects actual diffs and ordinary Git conflicts,
resolves overlaps, and regenerates shared derived artifacts once; `land`
merges the candidate into the tree the run stands on and runs the root's
`done` predicate there. An actual diff wider than Details predicted is
never by itself a rejection: Goal is the acceptance boundary.

## Template and executor form

A composition is `template.md` plus ticket stubs. `tickets.py instantiate`
substitutes placeholders, validates one acyclic graph with one terminal, seals
the exact snapshot, and writes all tickets or none.

`executor` names one registered callable verb or `script:<repo-relative path>`.
A multi-stage pack runs its declared `stages` in order through that one
child and one role ([roles.md](../rules/roles.md) §4); `orch-execute` and
`orch-check` read the stamped pack's craft and may not import a superseded
skill body or invent a second pack parser. Anything needing a fresh role or
independent verdict is a new ticket and child. Domains may add facts to
Context but do not replace the semantic sections.

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/work-item.md`. Rendered T0 shape; declaration drift is a validation error.

### `review_state`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | `orchflows.review.v1` |
| `records` | yes | — |

### `review_record_common`

| field | required | declared values |
| --- | --- | --- |
| `identity` | yes | — |
| `kind` | yes | `GatePlan`, `CritiqueAdjudication`, `RepairOutcome` |
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

### `review_aggregate_critique`

| field | required | declared values |
| --- | --- | --- |
| `accepted` | yes | — |
| `adjudicated_by` | yes | — |
| `adjudications` | yes | — |
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

### `ticket_assignment_sections`

| field | required | declared values |
| --- | --- | --- |
| `Goal` | yes | — |
| `Context` | yes | — |
| `Details` | no | — |

### `ticket_frontmatter`

| field | required | declared values |
| --- | --- | --- |
| `id` | yes | — |
| `run` | yes | — |
| `status` | yes | `pending`, `ready`, `claimed`, `suspended`, `complete`, `blocked`, `stalled`, `failed`, `limited` |
| `admission` | no | — |
| `executor` | yes | — |
| `pack` | no | — |
| `profile` | no | — |
| `independence` | no | — |
| `depends_on` | yes | — |
| `isolation` | no | — |
| `bound` | yes | — |
| `loop` | no | — |
| `done` | no | — |
| `checked_by` | no | — |
| `root_generation` | no | — |
| `cut_generation` | no | — |
| `assignment_seal` | no | — |
| `workspace_branch` | no | — |
| `workspace_baseline` | no | — |
| `dispatch_v1` | no | — |
| `review_order` | no | — |
| `review_v1` | no | — |
| `review_stage` | no | — |
| `review_kind` | no | `critique`, `repair`, `null` |

### `loop_stub`

| field | required | declared values |
| --- | --- | --- |
| `done` | yes | — |

### `done_binding`

| field | required | declared values |
| --- | --- | --- |
| `form` | yes | `command`, `check` |
| `value` | yes | — |

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

T0 supersession record sha256:e6843c614f8b944d55ad17b365053d8067da3b3c119930dcb74ec37e12c9374f:
the T0 shape is declared in contracts/shapes.json and renders this contract
section and its validator consumer.

T0 supersession record sha256:52c8d90678f197a32575769b3b6eaef9e4d9edcdead6d85fd74ee82aab449b6d:
the generated section wording is kept distinct from lifecycle prose while
remaining a deterministic declaration-to-consumer gate.

T0 supersession record sha256:2d090e77139a186a035e1ca293cc9a9ae53863f4c876ac983812ec77559e6d49:
the generated T0 section now uses declaration-specific wording.

T0 supersession record sha256:8926075889cc5c2614bb77dd16958956c028162ec8e1a31f8a63f9dbe588d63b:
the intake verb orch-spec is renamed orch-outline in the seven-verb registry.
The noun spec — a run's frozen statement — keeps its name, and so does the
pack's required_spec_fields cell. A dispatch naming the old verb refuses and
names the successor; nothing aliases it.

T0 supersession record sha256:60cec4c556056d0e2b903ec93fa9c06d994cf25d761215529567df7cd02e5594:
the loop engine is absorbed into the driver. The ticket gains the optional
loop object (loop_stub/loop_done shapes) and orch-loop leaves the callable
registry — six verbs remain; a dispatch naming it refuses toward the loop
field. No LLM holds loop state: scripts/tickets_loop.py arms, evaluates,
and advances, and the worklog is the state.

T0 supersession record sha256:e462edd95fa2a58bcb4836dffd9a23120b46dfca70dc0d0c904ae1e5e277e755:
the ticket diet: claimed_by and claimed_at leave the frontmatter — the
dispatch_v1 attempt's owner and opened_at were already the lease, and the
pair was a projection with a second owner; sequence retires — a multi-stage
pack's stages run in order at the head's one role, and the orch- prefix
wedge that classified chain entries goes with it; isolation becomes the
rare explicit override over the value derived from the stamped pack's
adapter.

T0 supersession record sha256:0fc272b985dbceb3b1cbcd3309109e254ee85fdee485fbc522262a68f64e2443:
`workspace_path` leaves the frontmatter. The dispatch attempt establishes
the tree and is now its sole owner, so the ticket's projection of the same
path — the second home that let a packet name a tree the establishment had
not created — is gone, and lint refuses the field. The Git-only
`workspace_branch` and `workspace_baseline` observations stay where they
were. Packet projection keeps its own section, without the receipt half the
dispatch contract retired.

T0 supersession record sha256:3f22969c019c621ea83e4e6d630ff1ddadc9ff4cce7a5ccbfc7da874a0419f37:
the packet projection section becomes the launch section. This ticket is the
assignment the dispatch contract's generated prompt points at, and nothing
copies it; the executor-record identities are the attempt's, carried into
that prompt with a `RECORD_ID` placeholder the child fills per write.

T0 supersession record sha256:b569907384410354a1abdd66c60a6a0264536243db41103f202b297853b27678:
the ticket gains the optional `done` predicate. It is the binding the loop
object already carried, promoted to the frontmatter and renamed
`done_binding` because it now has two homes and one grammar, and it joins
the sealed assignment fields: a changed `done` is a changed assignment.
`tickets.py land` is its only evaluator -- it merges the candidate into the
tree the run stands on, runs the command there, and files the exit as
system-written Verification -- and a refused command arms the next
`<id>.repair.NN` round rather than closing the item. Terminal status is that
predicate's reading or the driver's grade at the join, never the executor's
claim. `review_kind` loses `verify`, the review ledger ends at
`RepairOutcome`, and the `Verification` record and its shape are removed
with the standing verification lane they served.

T0 supersession record sha256:ae7a127d5d67fb0eb6cdbfde042427e17dba588a4c80cdd67baedf98f532f291:
the semantic ticket diet. `## Suggested files` becomes `## Details`, and what
it may hold stops being a non-binding path list: it is the planner's free-form
guidance for this one child -- read-lists, anchors, prescribed steps, do-nots,
definition-of-done commands, and what the closing report should carry. The
clauses that forbade all of it go with the section they qualified: the
assignment may now carry authored file paths, prescribed actions, named checks
and prescribed tests, and the executor no longer "chooses implementation, tests,
and verification" by law. What replaces the prohibition is the escape hatch --
follow Details and say so, or deviate where following it would miss Goal and
report the deviation -- because a planner that investigated should prescribe
and a planner that did not should leave the choice.

The five executor sections become one `## Report`. `Result`, `Verification`,
`Feedback`, `Risks` and `Handoff` are gone, with the `[]` prefill, the
`--section`, `--append` and `--replace` flags, and the `mode` and `section`
fields of the result record: there is one section, one mode, and no consumer
that reads which heading a fact arrived under. Outcome evidence is one closing
note appended there like any other filing, and the delta law is gone with the
five keys it policed. A critique's findings, the one thing a machine does read,
cross to the join as a file -- `--findings-file <path|->`, beside
`--accepted-file` -- and live in the `CritiqueAdjudication` that was always
their durable home. `land` appends its predicate reading to `Report`. No
instruction ceiling bounds any of it: `tickets.py new` and `lint` grade a
ticket's shape, never its length.
