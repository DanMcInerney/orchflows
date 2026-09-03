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
  role binding. Callable executors are the two registered verbs
  `orch-do` and `orch-judge`;
  `script:<repo-relative path>`
  is the only other executable form. Skill substitution is not allowed, and a
  superseded name is refused naming its successor rather than aliased.
- optional `pack_digest` — the stamped pack's content digest, taken at issue
  time and never afterwards. Every later command resolves the named pack and
  refuses when the two differ, so a pack that changed under a sealed
  assignment, or a nearer ring that came to shadow it, is a refusal rather
  than a substitution. A ticket naming no pack pins nothing.
- optional `sheets` and `sheet_digests` — the stamped sheets' names, and the
  content digest of each, taken at issue beside the pack's. A sheet is extra
  craft the caller stamps for this one assignment ([sheet.md](sheet.md)); a
  ticket stamping none carries neither field.
- optional `skill` and `skill_digest` — the applied skill this ticket's
  executor enters as its method, and that skill's content digest at issue.
  `executor` is unchanged: the kernel verb still owns the contract, and the
  applied skill is how the work is done inside it.
- optional `done` — the canonical JSON done predicate, `{"form", "value"}`:
  form `command`, a deterministic command whose exit 0 is the verdict, or
  form `check`, a criterion no oracle covers, judged by one minted
  `orch-judge` ticket. On an ordinary ticket `tickets.py land` is the only
  evaluator: it runs the
  command in the integrated tree, and that run is the one outside execution
  ([verification.md](../rules/verification.md) §6). A refused command arms
  the next `<id>.repair.NN` round rather than closing the ticket; two rounds
  with no result delta close it `stalled`. A ticket carrying no predicate is
  graded by the driver at the join instead.
- optional `makes` — the artifact kind a planning `do` produces, `root` or
  `cut`. Every craft's `## Lens` carries one entry per artifact kind its
  domain produces, and the dispatch names the entry this child works
  against: a `do` making the stamped pack's own deliverable takes the kind
  from the adapter and carries no marker, and a `judge` takes it from the
  typed identities on its Context. The marker exists for the one case
  neither answers — a `do` whose deliverable is a frozen root or a cut of
  work items, which no adapter names.
- optional `frame` — the marker `true`, and no other value. It says this
  ticket is one call-stack frame: the durable record of one workflow
  invocation, opened by `tickets.py frame-open` and closed by
  `tickets.py frame-close`. A frame binds no `executor` and stamps no
  `pack`, and both absences are the marker's meaning rather than an
  omission — nothing dispatches a frame, because the orchestrator session
  is what drives it, and a frame is a journal rather than craft-governed
  work. `executor` is required of every other ticket and of no frame. Its
  `## Report` is that journal: the driver appends one line per wave through
  `tickets.py result` and re-reads it at the start of the next wave, which
  is where a resumed — or a merely compacted — driver recovers what it
  decided. A frame closing over two or more `do` children is refused unless
  its subtree holds a judging child or its journal carries an
  `unjudged: <reason>` line.
- optional `parent` — the ticket this one was minted under at runtime. It
  makes the ticket tree the call tree: a callable opened by `tickets.py do` or
  `tickets.py judge` hangs under its caller, its id is auto-minted as
  `<parent>.<n>` (root ids `B<n>` when parentless), and it is sealed through
  the parent's own sealed generation rather than named in a sealed cut that
  closed before it existed. A ticket naming no parent is a root.
- optional `depends_on` — ticket ids that must complete first. A runtime
  child declares none: prose order in the calling workflow is what sequences
  callables, and the parent relays each result forward.
- `bound` — operational effort bound.
- `independence`, `isolation` — checker/gate mechanics, and the rare
  explicit workspace override; an absent `isolation` derives its effective
  value from the stamped pack's adapter (`establishes_isolation`), read
  through one derivation everywhere.
- `admission`, `root_generation`, `cut_generation`, `assignment_seal` — the
  deterministic generation, validation, seal, and admission records.
- `workspace_branch`, and `workspace_baseline` — lifecycle observations written
  by their owning tools. The claim lease — owner and opened time — and the
  established tree both live in the `dispatch_v1` attempt alone; the ticket
  carries no projection of either. `workspace.py establish` is the mechanical owner of the
  candidate an isolated item runs in: it derives, creates, and records that tree
  on the live attempt, and re-establishing it never restamps the baseline. The
  Git-only fields fix that candidate's branch and starting revision.
- `dispatch_v1` — the canonical JSON `orchflows.dispatch.v1` attempt record.
  It is operational state, excluded from the assignment fingerprint.

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

`review_v1`, its `GatePlan`/`CritiqueAdjudication`/`RepairOutcome` record
chain, the `checked_by` and `review_stage` frontmatter fields, and
`tickets.py check --stage <id>.check` -- the one surviving reader the
composite-gate deletion left standing -- are retired together. That
deletion removed the mechanical minting and adjudication that used to
build the chain and left the reader in place pending its own census: no
live command ever constructs a `GatePlan`-then-`CritiqueAdjudication` chain,
so a `<id>.check` ticket could carry the ledger `check` required only by
hand-edited state, which the host block forbids -- test-only reachability
is not liveness. A critique is a `judge` ticket and the repair answering it
a `do` ticket, sequenced by the calling workflow's prose, and either
reaches its caller the ordinary way: the executor's `## Report` and the
joined disposition `land` records, never a distinct adjudication carrier.

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
reading to the same section, attributed to the driver that ran it, and -- where
a landing is refused on a merge conflict and later carried through -- the
conflicted paths and then the candidate revision the resolution delivered
beside the integrated revision it merged, each filed once however often it is
observed.

## Roots, decomposition, and integration

A root is the ticket named by a `root_generation` and may bind any lawful
registered executor; it owns the whole artifact. Decomposition retired with
orch-slice, its only minter (W4a): every root is direct now, and a runtime
child declares its `parent` and binds through that parent's seal rather than
through a cut a decomposer wrote.

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

A workflow is a skill whose prose opens a frame and calls callables
([vocabulary.md](../docs/vocabulary.md#structure)); `tickets.py instantiate`
and the `template.md`-plus-stubs shape it used to substitute and seal
retired with the decomposed-root concept they served (W4a).

`executor` names one registered callable verb or `script:<repo-relative path>`.
A multi-stage pack runs its declared `stages` in order through that one
child and one role ([roles.md](../rules/roles.md) §4); `orch-do` and
`orch-judge` read the stamped pack's craft and may not import a superseded
skill body or invent a second pack parser. Anything needing a fresh role or
independent verdict is a new ticket and child. Domains may add facts to
Context but do not replace the semantic sections.

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/work-item.md`. Rendered T0 shape; declaration drift is a validation error.

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
| `pack_digest` | no | — |
| `sheets` | no | — |
| `sheet_digests` | no | — |
| `skill` | no | — |
| `skill_digest` | no | — |
| `profile` | no | — |
| `independence` | no | — |
| `parent` | no | — |
| `depends_on` | no | — |
| `isolation` | no | — |
| `bound` | yes | — |
| `frame` | no | `true` |
| `done` | no | — |
| `makes` | no | `root`, `cut` |
| `root_generation` | no | — |
| `cut_generation` | no | — |
| `assignment_seal` | no | — |
| `workspace_branch` | no | — |
| `workspace_baseline` | no | — |
| `dispatch_v1` | no | — |

### `done_binding`

| field | required | declared values |
| --- | --- | --- |
| `form` | yes | `command`, `check` |
| `value` | yes | — |

<!-- END GENERATED T0 SHAPES -->
