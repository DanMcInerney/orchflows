# Dispatch contract

`orchflows.dispatch.v1` is the sole role-bearing communication protocol. This
contract owns its closed wire and persisted shapes; tickets bind the record but
do not redefine it.
The generated [dispatch lifecycle cells](../docs/lifecycle.md#ticket-lifecycle)
place those records between their authorized predecessor and result states.

## Persisted state

`dispatch_v1` is canonical JSON with exactly `protocol` and `attempts`.
`protocol` is `orchflows.dispatch.v1`; `attempts` is a non-empty ordered list
with unique `dispatch_id` values and at most one `state: live` member.

Each attempt has exactly `assignment_seal`, `dispatch_id`, `owner`, absolute
`opened_at`, absolute `lease_expires_at`, `outcome_record_id: outcome`, `state`,
and `records`, plus only the transition fields applicable to retirement or
replacement. States are `live`, `retired`, and `replaced`; clock expiry never
writes an implicit state transition. Each record has exactly `record_id`, `kind`, canonical-JSON
`content`, absolute `committed_at`, and stored `success`. Record ids are unique
within an attempt. Kinds are `generic`, `packet`, `result`, `outcome`,
`join`, and `lifecycle`; `dispatch-packet`, `outcome`,
`join:*`, and `lifecycle:*` are reserved for their owning operations.
Execution events are an ordered grammar, not a bag: the committed packet
precedes every result record; the one outcome follows results; join follows
outcome. Reordering them makes the whole persisted state invalid without
mutation.

Every read and mutation validates the whole closed state first. Record content
and stored success are closed per kind and must agree with ticket origin,
attempt identity, transition, and replacement edges. Unknown fields, malformed
members, duplicate identities, multiple live attempts, invalid absolute times,
invalid transition states, orphan replacement edges, forged successes, and
non-canonical encodings are `dispatch-record-invalid`; refusal preserves ticket
bytes.

## Attempt precedence

The public state operations are `dispatch-open`, `dispatch-commit`,
`dispatch-retire`, and `dispatch-replace`; each admits only its owned shape and
record namespace.

An exact committed `(dispatch_id, record_id)` and content returns stored success
even after expiry, retirement, or replacement. Different content at that pair
is `idempotency-conflict`. Only then may an unseen record be classified as
`dispatch-mismatch`, `assignment-mismatch`, or `stale-attempt`. A second live
attempt is `live-attempt`. Opening, replacing, retiring, outcome import, and
joining are atomic ticket writes. Expiry makes unseen work stale but does not
authorize or persist a successor: the expired live attempt must cross
`dispatch-retire` or the atomic `dispatch-replace` transition first. Replacing
an attempt still inside its lease supersedes authorized work, and silence is
not evidence that work stopped: it is `supersession-undeclared` unless the
caller declares it with `--supersede-live`. The
absolute lease is never extended by transport or result motion.

Facade transactions order side effects after the last refusable check; a
failed step surfaces its own error plus any failed cleanup; every step
replays idempotently. A composition over these operations therefore replays
as a whole, and reports which of its steps it found already done.

## Packet

`dispatch-packet` commits the projection, and that committed record is the
whole packet: nothing validates a packet a caller carries back. The public
command emits ASCII-escaped canonical JSON, preserving every packet character
independently of the subprocess code page.

A packet has exactly `protocol`, `source`, `dispatch_id`, `assignment_seal`,
`lease_expires_at`, `role`, `assigned_name`, `workspace`, `pack`, `prompt`,
`review_kind`, and `durability` — the identities a child cannot derive from
the ticket it is pointed at, and nothing it can. `review_kind` is null for an
ordinary execution packet or one of `critique`, `repair`, and `verify` for a
typed review lane. `source` is an exact `{run,id}` object, and
`durability` is `ticket`: work carrying no ticket is outside this protocol.
There is no return-address field: a child's return is its records, and the
harness notifies its caller.

Projection refuses `state-inaccessible` when the sink holding the ticket
cannot be read, `review-invalid` when the ticket's review ledger does not
admit this lane, and `workspace-unestablished` or `workspace-mismatch` when
the named tree is not the candidate the establishment recorded.

A dispatched child proves who it is the same way on its first write as on
every later one, by naming `(dispatch_id, assignment_seal, --by)`; the first
record it files is its acceptance, and there is no separate accept step to
run, to run from the wrong directory, or to refuse.

## Outcome and join

Every attempt reserves exactly one durable return identity, `outcome`. Its
closed envelope has exactly `protocol`, `run`, `id`, `assignment_seal`,
`dispatch_id`, `outcome_record_id`, `by`, `status`, and `evidence`. Evidence has
exactly string bodies for `Result`, `Verification`, `Feedback`, `Risks`, and
`Handoff`; the first four are non-empty, Handoff is non-empty only for
`suspended`. Evidence is the non-empty closing delta not already materialized
through result records; repeated material is refused so each item is written
once. `dispatch-outcome` validates the envelope, imports its attributed
evidence atomically, and commits or replays the reserved outcome record. A
child commits it directly, and a coordinator relaying for one passes the same
envelope through `--file` rather than inventing another payload.

`dispatch-join` consumes only that distinguished record and derives disposition
from it. Its id is `join:outcome`; exact replay returns stored success after
retirement, changed join content conflicts, and an unseen join on an ended
attempt is stale. Only join writes suspended or terminal ticket status. Every
joined disposition, including suspension, retires its attempt; suspension
retains claimant observations for handoff but leaves no live dispatch.
For review-stage tickets the same atomic join also advances the ticket's
validated `orchflows.review.v1` chain: critique requires the canonical accepted
subset from the file-based `--accepted-file <path|->` seam, repair requires the
exact output artifact, and verification must match that artifact and carry a
`PASS`, `FAIL`, or `UNVERIFIED` verdict. Every review kind has one closed field
schema, and the ledger tip equals the
protocol-owned join's `review_identity`. `GatePlan` seals the normalized
workspace; a code artifact is a full Git commit that resolves to that
workspace's exact HEAD before packet commit and after repair.

The ordinary checker is a derived `<id>.check` review-stage ticket. It uses
the same committed packet, outcome, and join as gate review.
Only `check <run> <id> --stage <id>.check` attaches its authenticated receiver
identity to the target's `checked_by`; direct caller-supplied findings are not
a protocol operation.

## Cutover

The public facade has no role-bearing `claim` or legacy `packet` route and no
dual reader. A claimed or suspended ticket without this record is
`claim-without-dispatch`: a live claim exists only as a dispatch-v1 attempt,
and the attempt's `owner` and `opened_at` are the lease — the ticket carries
no projection of them. History is never inferred or rewritten.

T0 supersession record sha256:82cecc2a7e182409496a6ed451f9121bfb990ab0bf7ca9e69012073093f8be67:
persisted dispatch semantics now close every record kind and stored success,
require explicit expiry transitions, retire suspension, and materialize only
unstreamed outcome evidence; receiver acceptance is a reserved durable attempt
record required before result, outcome, or join; packet carriage is canonical
ASCII output plus UTF-8 file or standard input, and unauthenticated offline
inline receipt is refused.

T0 supersession record sha256:008949dad0a49ab76c5bf65645081a895add5e2d2116032c653061c0b0aeafde:
review-stage joins bind the accepted blocker subset and exact repair or
verification artifact through the ticket's predecessor-linked review ledger.

T0 supersession record sha256:fc3cbeefa9b42ca373758739a79cb092ea5512cd850e09bb6d3d6b32e380691b:
packet projections carry one typed `review_kind`; execute and check routing
consumes the resolved pack cells for that lane, with no legacy checker aliases.

T0 supersession record sha256:69b9e37a924419da4aa7a549a611d1ed14c478228b4b702b50f08c1e9a3c7a68:
the T0 shape is declared in contracts/shapes.json and renders this contract
section and its validator consumer.

T0 supersession record sha256:7d04c3500b8d99d51df777df123d2f31e01e5af2b18a196337f78a98bcd2ea7c:
the generated section wording is kept distinct from lifecycle prose while
remaining a deterministic declaration-to-consumer gate.

T0 supersession record sha256:e26b5916a54fd4b95c20790abb7aa55173782d0454576b8cf77cf0e0edbe46ac:
the generated T0 section now uses declaration-specific wording.

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/dispatch.md`. Rendered T0 shape; declaration drift is a validation error.

### `dispatch_state`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | `orchflows.dispatch.v1` |
| `attempts` | yes | — |

### `dispatch_attempt`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `lease_expires_at` | yes | — |
| `opened_at` | yes | — |
| `outcome_record_id` | yes | `outcome` |
| `owner` | yes | — |
| `records` | yes | — |
| `state` | yes | `live`, `retired`, `replaced` |
| `retired_at` | no | — |
| `retirement` | no | — |
| `replaced_at` | no | — |
| `replaced_by` | no | — |
| `replacement` | no | — |
| `replaces` | no | — |

### `dispatch_record`

| field | required | declared values |
| --- | --- | --- |
| `committed_at` | yes | — |
| `content` | yes | — |
| `kind` | yes | `generic`, `packet`, `result`, `outcome`, `join`, `lifecycle` |
| `record_id` | yes | — |
| `success` | yes | — |

### `dispatch_stored_success`

| field | required | declared values |
| --- | --- | --- |
| `committed_record` | yes | — |

### `dispatch_committed_record`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `run` | yes | — |
| `id` | yes | — |
| `dispatch_id` | yes | — |
| `record_id` | yes | — |
| `content` | yes | — |

### `dispatch_packet_record`

| field | required | declared values |
| --- | --- | --- |
| `packet` | yes | — |

### `dispatch_result_record`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `body` | yes | — |
| `mode` | yes | — |
| `operation` | yes | — |
| `section` | yes | — |
| `writer` | yes | — |

### `dispatch_result_success`

| field | required | declared values |
| --- | --- | --- |
| `result` | yes | — |

### `dispatch_result_projection`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `run` | yes | — |
| `id` | yes | — |
| `path` | yes | — |
| `section` | yes | — |
| `mode` | yes | — |
| `by` | yes | — |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `record_id` | yes | — |

### `dispatch_transition_success`

| field | required | declared values |
| --- | --- | --- |
| `dispatch` | yes | — |

### `dispatch_retirement_dispatch`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `outcome` | yes | `retired` |
| `run` | yes | — |
| `id` | yes | — |
| `dispatch_id` | yes | — |
| `record_id` | yes | — |
| `retired_at` | yes | — |
| `state` | yes | `retired` |

### `dispatch_replacement_dispatch`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `outcome` | yes | `replaced` |
| `run` | yes | — |
| `id` | yes | — |
| `dispatch_id` | yes | — |
| `record_id` | yes | — |
| `replaces` | yes | — |
| `assignment_seal` | yes | — |
| `lease_expires_at` | yes | — |
| `opened_at` | yes | — |
| `state` | yes | `live` |

### `dispatch_join_content`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `joined_by` | yes | — |
| `operation` | yes | — |
| `outcome_record_id` | yes | — |
| `review` | no | — |

### `dispatch_retire_request`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `operation` | yes | `retire` |

### `dispatch_replace_request`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `lease_expires_at` | yes | — |
| `operation` | yes | `replace` |
| `owner` | yes | — |
| `replaces` | yes | — |

### `dispatch_join_success`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `run` | yes | — |
| `id` | yes | — |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `outcome_record_id` | yes | — |
| `by` | yes | — |
| `status` | yes | — |
| `joined_at` | yes | — |
| `review_identity` | no | — |

### `dispatch_packet`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `source` | yes | — |
| `dispatch_id` | yes | — |
| `assignment_seal` | yes | — |
| `lease_expires_at` | yes | — |
| `role` | yes | — |
| `assigned_name` | yes | — |
| `workspace` | yes | — |
| `pack` | yes | — |
| `prompt` | yes | — |
| `review_kind` | yes | `critique`, `repair`, `verify`, `null` |
| `durability` | yes | `ticket` |

### `dispatch_outcome`

| field | required | declared values |
| --- | --- | --- |
| `protocol` | yes | — |
| `run` | yes | — |
| `id` | yes | — |
| `assignment_seal` | yes | — |
| `dispatch_id` | yes | — |
| `outcome_record_id` | yes | — |
| `by` | yes | — |
| `status` | yes | `complete`, `blocked`, `stalled`, `limited`, `failed`, `suspended` |
| `evidence` | yes | — |

### `dispatch_outcome_evidence`

| field | required | declared values |
| --- | --- | --- |
| `Result` | yes | — |
| `Verification` | yes | — |
| `Feedback` | yes | — |
| `Risks` | yes | — |
| `Handoff` | yes | — |

<!-- END GENERATED T0 SHAPES -->
