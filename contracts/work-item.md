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
- `review_order` — the sealed zero-based order of a composite-gate lens.
- `admission`, `root_generation`, `cut_generation`, `assignment_seal` — the
  deterministic generation, validation, seal, and admission records.
- `claimed_by`, `claimed_at`, `checked_by`, `workspace_branch`, and
  `workspace_baseline` — lifecycle observations written by their owning tools.
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
