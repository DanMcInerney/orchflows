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
- `dispatch_v1` — the canonical JSON `orchflows.dispatch.v1` attempt record.
  It is operational state, excluded from the assignment fingerprint.

`status` is `pending`, `ready`, `claimed`, `suspended`, `complete`, `blocked`,
`stalled`, `failed`, or `limited`. Admission alone creates `ready`; claim alone
creates `claimed`; the join alone records terminal status.

Sealing fingerprints Goal, Context, optional Suggested files, exact executor,
dependencies, and necessary system identity. It never creates file authority
or a prescribed test oracle. Accepted generation identity is immutable;
compare-and-swap sealing refuses a stale snapshot.

## Dispatch-v1 attempt state

One ticket has one authoritative `dispatch_v1` record and at most one live
**dispatch attempt**. `dispatch-open` atomically records `dispatch_id`, the
current `assignment_seal`, owner, opening time, and absolute
`lease_expires_at` while creating `claimed`. Delivery retries reuse the same
`dispatch_id`; a new attempt after retirement or replacement uses a new one.
`dispatch-replace` ends the named live attempt and opens its unique successor
in the same ticket write. `dispatch-retire` durably ends the named attempt.

`dispatch-commit` keys a committed record by `dispatch_id` plus `record_id`.
Precedence is fixed: an exact committed pair and content returns its stored
success even after retirement, replacement, or lease expiry; changed content
for that pair is `idempotency-conflict`. Only then does the command classify
an unknown id as `dispatch-mismatch`, a changed seal as
`assignment-mismatch`, or an unseen record on an expired, retired, or replaced
attempt as `stale-attempt`. A different attempt while one is live is
`live-attempt`. Every refusal leaves the ticket byte-identical.

A claimed or suspended historical ticket with no `dispatch_v1` is
`legacy-live-claim` at every dispatch-v1 operation. Its existing owner must
complete or abandon it before installation of a v1 attempt. No command infers
an attempt, reconstructs history, or rewrites historical state.

## Dispatch-v1 packet projection and receipt

`dispatch-packet` commits exactly one `dispatch-packet` record for a live
attempt, then returns its stored packet projection. An exact delivery retry
replays that stored projection even after the attempt ends; different form,
reply target, or workspace authority for the same record is
`idempotency-conflict`. The projection fields are generated, never repaired in
transport:

- `protocol`, `dispatch_id`, `assignment_seal`, and absolute
  `lease_expires_at` identify the fenced attempt.
- `executor`, `role`, `profile`, `assigned_name`, `reply_to`, and `workspace`
  bind the exact child identity and authority; `pack`, `independence`,
  `isolation`, and `admission` carry its admitted execution mechanics.
- `form` is `reference` or `inline`; `durability` is `ticket` or `ephemeral`.
  `source` names the originating ticket. A `reference` names that ticket by
  `run` and `id`. An `inline` carries the immutable semantic assignment and
  the same `assignment_seal`.

`dispatch-receive` validates protocol, form, lease, seal, committed projection,
assigned identity, resolved role and profile, reply target, and workspace
authority before execution. Unknown or malformed traffic is `packet-invalid`;
an unavailable referenced ticket is `state-inaccessible`; a changed reference
or inline snapshot is `assignment-divergent`; actual child name, role, profile,
or authority disagreements are `identity-mismatch`, `role-mismatch`,
`profile-mismatch`, or `authority-mismatch`. An ended attempt is
`stale-attempt`. No refusal changes ticket state.

Reference is the default. Inline is the fallback when the receiver cannot read
the state sink: it can prove the sealed snapshot and absolute lease but reports
that durable state was not checked, so a later result still crosses the
authoritative attempt seam. An inline packet with `durability: ephemeral` has
no ticket, crash recovery, resumption, or durable stale-lane evidence.

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

T0 supersession record sha256:1d95dfb82a4489f5d05d067d36fc669720c18424359d8b8c84f0857bde3a53fb: `dispatch_v1` adds the sole atomic execution-attempt and committed-record seam.

T0 supersession record sha256:d12f7cb34c27575e52f78faf4aa5348d1c5ee35f5f14bf9fc502103560435fe5: dispatch-v1 adds committed reference or inline packet projection and deterministic receipt validation.
