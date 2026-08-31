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
and `records`, plus the `workspace_path` its establishment recorded and only
the transition fields applicable to retirement or replacement. The attempt is
that path's sole owner: the ticket carries no projection of it. States are `live`, `retired`, and `replaced`; clock expiry never
writes an implicit state transition. Each record has exactly `record_id`, `kind`, canonical-JSON
`content`, absolute `committed_at`, and stored `success`. Record ids are unique
within an attempt. Kinds are `generic`, `launch`, `result`, `outcome`,
`join`, and `lifecycle`; `launch`, `outcome`,
`join:*`, and `lifecycle:*` are reserved for their owning operations.
Execution events are an ordered grammar, not a bag: the committed launch
precedes every result record; the one outcome follows results; join follows
outcome. Reordering them makes the whole persisted state invalid without
mutation.

A record's content is stored once, as that canonical string. Stored success
carries the record's identity and never a second copy of what it committed;
a caller that wants the content reads the record.

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

## Launch

There is no wire object. The sealed ticket is the assignment, and `dispatch`
is one lock over readiness, the minted attempt, the established workspace, and
one committed `launch` record: `host`, `verb`, `agent`, `model`, `effort`,
native `fields`, and the generated `prompt`. That prompt is the whole
child-facing instruction surface, so an orchestrator invokes the launch
verbatim and hand-adds nothing; a caller who lost it replays the same
`dispatch` call and is handed the committed launch back unchanged.

The prompt names, once each, what a child cannot derive: the ticket's absolute
path inside the established workspace, that workspace and the instruction to
run from inside it, this host's verified interpreter, the resolved pack craft,
the review lane's root ticket path, the assigned name, the lease deadline, the
filled filing and closing commands, the craft's verification scope, what a
report is expected to carry, and that
every check runs to completion in the turn it starts. It teaches no verdict
token and no filing taxonomy: a child files evidence into one channel, never a
disposition and never a heading of the protocol's choosing. It names no skill for
the child to invoke and no pack for it to resolve: it hands the paths. The
public command emits ASCII-escaped canonical JSON, preserving every prompt
character independently of the subprocess code page.

Three of those lines exist so a parent can read a child's answer without
paraphrasing it. The child is told to commit its work inside the candidate
before closing and to name that commit in the closing note; it is told to
print one verbatim artifact line, `artifact: <kind>:<identity>`, whose kind
the stamped pack's adapter fixes — `git` a full commit id, `doc` a
`<path>@sha256:<digest>` over the document bytes at close, `evidence` a store
id; and a review lane is told to print `findings: <path>` as a second
verbatim line. The digest a `doc` identity carries is declared, not verified:
the child computes it, and no door yet recomputes it.

Dispatch refuses `state-inaccessible` when the sink holding the ticket cannot
be read, `review-invalid` when the ticket's review ledger does not admit this
lane, and `workspace-unestablished` or `workspace-mismatch` when the named
tree is not the candidate the establishment recorded.

A dispatched child proves who it is the same way on its first write as on
every later one, by naming `(dispatch_id, assignment_seal, --by)`; the first
record it files is its acceptance, and there is no separate accept step to
run, to run from the wrong directory, or to refuse.

## Outcome and join

Every attempt reserves exactly one durable return identity, `outcome`. Its
closed envelope has exactly `protocol`, `run`, `id`, `assignment_seal`,
`dispatch_id`, `outcome_record_id`, `by`, and `evidence`. Evidence is one
non-empty string: the child's closing note, in whatever form it judges useful,
appended to `Report` like every other filing. Nothing parses it, so nothing
compares it against what already streamed. The envelope names no disposition:
its existence closes the attempt and says nothing about what the item became.
`dispatch-outcome` validates the envelope, imports its attributed
evidence atomically, and commits or replays the reserved outcome record. A
child commits its note through `--note` or `--note-file`, and a coordinator
relaying for one passes the whole canonical envelope through `--file` rather
than inventing another payload.

`dispatch-join` consumes only that distinguished record and records the
disposition `--status` names. Its id is `join:outcome`; exact replay returns
stored success after
retirement, changed join content conflicts, and an unseen join on an ended
attempt is stale. Only join writes suspended or terminal ticket status. Every
joined disposition, including suspension, retires its attempt; suspension
retains claimant observations for handoff but leaves no live dispatch.
The join reads the tree the item was executed in off the attempt.
For review-stage tickets the same atomic join also advances the ticket's
validated `orchflows.review.v1` chain: critique requires the canonical complete
findings and accepted subset from the file-based `--findings-file <path|->` and
`--accepted-file <path|->` seams, and repair requires
the exact output artifact. The chain ends there. Every review kind has one
closed field schema, and the ledger tip equals the
protocol-owned join's `review_identity`. A review lane's prompt names that
ledger by the ticket path holding it and by its tip identity; the chain
itself is never copied. `GatePlan` seals the normalized
workspace; a code artifact is a full Git commit that resolves to that
workspace's exact HEAD before launch and after repair.

Every fixed artifact identity a join binds is the typed line its adapter
fixes, and the prefix is graded wherever the Git one was: a `git-commit`
adapter still takes `git:<full-commit-id>` and still resolves it against the
sealed workspace HEAD, a `document-revision` adapter takes `doc:` and an
`evidence-packet` adapter takes `evidence:`, each non-empty after the colon.
An untyped identity is refused rather than accepted as prose.

The ordinary checker is a derived `<id>.check` review-stage ticket. It uses
the same committed launch, outcome, and join as gate review.
Only `check <run> <id> --stage <id>.check` attaches its authenticated receiver
identity to the target's `checked_by`; direct caller-supplied findings are not
a protocol operation.

## Cutover

The public facade has no role-bearing `claim` route, no packet route, and no
dual reader. A claimed or suspended ticket without this record is
`claim-without-dispatch`: a live claim exists only as a dispatch-v1 attempt,
and the attempt's `owner` and `opened_at` are the lease — the ticket carries
no projection of them. History is never inferred or rewritten.

T0 supersession record sha256:e6fb8d96d9fb66051be6abd8a773369a4939b8a0ba896ac0c66604b446870b42:
artifact identities become typed per adapter, and the prompt gains the three
lines that make a parent's relay mechanical: commit inside the candidate
before closing, one verbatim `artifact:` line whose kind the adapter fixes,
and for a judging lane one verbatim `findings:` line. Every door that bound a
Git identity now grades the adapter's own prefix instead of accepting any
non-empty string outside the Git lane. A `doc` identity's digest is declared
by the child and recomputed nowhere.

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

T0 supersession record sha256:8b9d58a02911955ff011275988aba554c8b502557348009f7fe1bf268414e0a5:
the receipt handshake and the inline packet form are removed. The `receipt`
record kind, the `dispatch-receipt` reserved id, and the refusals that
existed only for the handshake ride out with them; a child's first filed
record is its acceptance, proved by the `(dispatch_id, assignment_seal,
--by)` every write already carries, and the one surviving ordering rule is
that a committed packet precedes every execution record. The wire keeps
twelve fields: `form`, `inline`, `reference`, `reply_to`, `admission`,
`independence`, `isolation`, `executor`, `profile`, and
`outcome_record_id` had no reader left, and `durability` declares only
`ticket`. The attempt gains the `workspace_path` its establishment records
and becomes that path's sole owner. A committed record's content is stored
once, and a review lane's packet names its ledger by ticket path and tip
identity rather than copying the chain.

T0 supersession record sha256:441bc5276a8ba5e7f92a76163d7deedcf764781f13ad94c60f4fed89824f9f5a:
the packet is not a wire object any more; it is not an object at all. The
`dispatch_packet` shape, its twelve remaining fields, the `dispatch-packet`
verb, and the `--packet-file` carriage are removed, and the `packet` record
kind is renamed `launch` and reshaped to the emitted invocation: `host`,
`verb`, `agent`, `model`, `effort`, native `fields`, and the generated
`prompt`. `dispatch` is the one operation that commits it, under one run
lock, and replaying that call returns the committed launch unchanged. The
prompt becomes the whole child-facing instruction surface and carries, once
each, the facts a child cannot derive: its ticket's absolute path, the
established workspace, this host's verified interpreter, the resolved pack
craft and that craft's verification-scope sentence, a review lane's root
ticket path, the assigned name, the lease deadline, the filled filing and
closing commands, and the turn-completion rule for every check. The launch
record carries no identity of its own: its stored success binds it to the
attempt, and the join reads the executed tree off the attempt's
`workspace_path` rather than off any record.

T0 supersession record sha256:6c60b8402bfe79e2ed262b91c512471c2b850d5fca73403ce8c9a73ae7309308:
the closing envelope no longer names a disposition. `status` leaves the
`dispatch_outcome` shape and the whole typed-close flag it selected, so an
outcome's existence closes the attempt and says nothing more; `Handoff`
stops being coupled to a disposition the envelope cannot carry and is
simply optional evidence. `dispatch-join` takes the disposition it records
through a required `--status`, and `dispatch_join_success` is that value's
one declaring home. The review chain ends at `RepairOutcome`: the
`Verification` record kind, its shape, the `verify` review kind, and the
`PASS`/`FAIL`/`UNVERIFIED` verdict token the join used to parse out of a
child's prose are all removed, and the prompt teaches no token in their
place. The fresh outside check is the landed ticket's own `done` predicate,
run by `land` in the tree it has just merged the candidate into.

T0 supersession record sha256:83bebaf00635c6cb8e2b6f6681024c6ea7f8ca35196b5e3efcfff69dc006ff15:
the return has one channel. `dispatch_outcome_evidence` is gone: `evidence` is
one non-empty string, the child's closing note, and the five typed close flags
become `--note` and `--note-file` while `--file` keeps relaying a whole
canonical envelope. Nothing parses that note, so the delta rule that refused a
repeat of already-streamed evidence is gone with the sections it compared.
`dispatch_result_record` and `dispatch_result_projection` lose `section` and
`mode` for the same reason -- one section, one mode, both constants restated on
the wire. A critique's complete findings reach `dispatch-join` through
`--findings-file <path|->` beside the accepted subset's `--accepted-file`,
rather than being read back out of the records the child streamed. The prompt
names what a report is expected to carry and teaches no filing taxonomy.

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
| `workspace_path` | no | — |
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
| `kind` | yes | `generic`, `launch`, `result`, `outcome`, `join`, `lifecycle` |
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

### `dispatch_launch_record`

| field | required | declared values |
| --- | --- | --- |
| `launch` | yes | — |

### `dispatch_result_record`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `body` | yes | — |
| `operation` | yes | — |
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
| `status` | yes | `complete`, `blocked`, `stalled`, `limited`, `failed`, `suspended` |
| `joined_at` | yes | — |
| `review_identity` | no | — |

### `dispatch_launch`

| field | required | declared values |
| --- | --- | --- |
| `host` | yes | — |
| `verb` | yes | — |
| `agent` | yes | — |
| `model` | yes | — |
| `effort` | yes | — |
| `fields` | yes | — |
| `prompt` | yes | — |

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
| `evidence` | yes | — |

<!-- END GENERATED T0 SHAPES -->
