# Work-item contract (ticket)

A ticket is one sealed semantic assignment plus system-owned lifecycle state.

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
  role binding. Skill substitution is not allowed.
- `depends_on` — ticket ids that must complete first.
- `bound` — operational effort bound.
- `independence`, `isolation` — checker/gate and workspace mechanics.
- `admission`, `root_generation`, `cut_generation`, `assignment_seal` — the
  deterministic generation, validation, seal, and admission records.
- `claimed_by`, `claimed_at`, `checked_by`, `workspace_branch`, and
  `workspace_baseline` — lifecycle observations written by their owning tools.

`status` is `pending`, `ready`, `claimed`, `suspended`, `complete`, `blocked`,
`stalled`, `failed`, or `limited`. Admission alone creates `ready`; claim alone
creates `claimed`; the join alone records terminal status.

Sealing fingerprints Goal, Context, optional Suggested files, exact executor,
dependencies, and necessary system identity. It never creates file authority
or a prescribed test oracle. Accepted generation identity is immutable;
compare-and-swap sealing refuses a stale snapshot.

## Executor records

After the semantic sections, tickets carry executor-owned `## Result`,
`## Verification`, `## Feedback`, and `## Risks`; `## Handoff` is optional.
They are append-only after seal and are excluded from assignment fingerprints.
The executor files them as work is produced through `tickets.py result --by <claimed_by>`
under [result.md](result.md). `Feedback` and `Risks` use `[]` when empty.

## Roots, decomposition, and integration

A root is the ticket named by a `root_generation`. A direct root may bind any
lawful registered executor and owns the whole artifact. A decomposed root binds
`orch-decompose`; every member and gate ticket uses this same semantic shape.

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

`executor` names an exact skill or `script:<repo-relative path>`. Optional
`sequence` lists exact ordered skills with its head equal to `executor`; every
skill must be callable by the bound role. Domains may add facts to Context but
do not replace the semantic sections.

## T0 supersession

A named-field change to this contract is an explicit T0 supersession. There is
one current reader and writer: no compatibility aliases, dual parsing, or
migration mode. Historical user state is not rewritten.

T0 supersession record sha256:b2d5d570a37764b9c83f305eaf90a98f604ce98c5d479ecbd7abb1059b9c94aa: executor records now enter through the attributed result writer.
