# Dispatch contract

`orchflows.dispatch.v1` is the sole role-bearing communication protocol. This
contract owns its closed wire and persisted shapes; tickets bind the record but
do not redefine it.

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
within an attempt. Kinds are `generic`, `packet`, `result`, `outcome`, `join`,
and `lifecycle`; `dispatch-packet`, `outcome`, `join:*`, and `lifecycle:*` are
reserved for their owning operations.

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
`dispatch-retire` or the atomic `dispatch-replace` transition first. The
absolute lease is never extended by transport or result motion.

## Packet and receipt

`dispatch-packet` commits the projection and `dispatch-receive` validates it
against the actual established child before execution.

A packet has exactly the common fields `protocol`, `source`, `dispatch_id`,
`assignment_seal`, `outcome_record_id`, `lease_expires_at`, `executor`, `role`,
`profile`, `assigned_name`, `reply_to`, `workspace`, `pack`, `independence`,
`isolation`, `admission`, `prompt`, `form`, and `durability`, plus exactly one
of `reference` or `inline`. Source and reference are exact `{run,id}` objects.

Reference is the default and is checked against the committed packet record.
Inline is a ticket-durable fallback: `inline` has exactly `assignment` and
`envelope_seal`; that seal binds assignment, source, dispatch, assignment,
lease, outcome, owner, role, profile, reply target, workspace, and durability.
A ticket packet cannot be downgraded to ephemeral. When its sink is unavailable,
receipt may report `state_sink_checked: false`, but the returned outcome still
imports through the original ticket attempt. Packet-only ephemeral work is
outside this ticket protocol.

Receipt success has exactly `protocol`, `outcome: accepted`, `dispatch_id`,
`assignment_seal`, `form`, `durability`, and `state_sink_checked`. Refusal has
`protocol`, `code`, and `error`. Unknown packet fields or shapes are
`packet-invalid`; other codes are `state-inaccessible`, `assignment-divergent`,
`stale-attempt`, `identity-mismatch`, `role-mismatch`, `profile-mismatch`, and
`authority-mismatch`.

## Outcome and join

Every attempt reserves exactly one durable return identity, `outcome`. Its
closed envelope has exactly `protocol`, `run`, `id`, `assignment_seal`,
`dispatch_id`, `outcome_record_id`, `by`, `status`, and `evidence`. Evidence has
exactly string bodies for `Result`, `Verification`, `Feedback`, `Risks`, and
`Handoff`; the first four are non-empty, Handoff is non-empty only for
`suspended`. Evidence is the non-empty closing delta not already materialized
through result records; repeated material is refused so each item is written
once. `dispatch-outcome` validates the envelope, imports its attributed
evidence atomically, and commits or replays the reserved outcome record. Thus a
reference child may commit directly and an offline inline child may return the
same envelope for its coordinator to relay without inventing another payload.

`dispatch-join` consumes only that distinguished record and derives disposition
from it. Its id is `join:outcome`; exact replay returns stored success after
retirement, changed join content conflicts, and an unseen join on an ended
attempt is stale. Only join writes suspended or terminal ticket status. Every
joined disposition, including suspension, retires its attempt; suspension
retains claimant observations for handoff but leaves no live dispatch.

## Cutover

The public facade has no role-bearing `claim` or legacy `packet` route and no
dual reader. A historical claimed or suspended ticket without this record is
`legacy-live-claim`; its existing owner must complete or abandon it before
installation. History is never inferred or rewritten.

T0 supersession record sha256:82cecc2a7e182409496a6ed451f9121bfb990ab0bf7ca9e69012073093f8be67: persisted dispatch semantics now close every record kind and stored success, require explicit expiry transitions, retire suspension, and materialize only unstreamed outcome evidence.
