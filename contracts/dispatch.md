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
mutation. A frame's attempt ([work-item.md](work-item.md)'s `frame` marker)
is the one attempt that opens with no launch, because nothing is dispatched
for it: the driver is the session that opened the frame, and its journal,
outcome, and join begin the grammar. The rest of the ordering is unchanged
and is enforced for a frame exactly as for a launched attempt.

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

A run's git integration target -- the checkout and branch `land` merges
candidates into -- is fixed once, by the first establishment whose caller
named the tree it cuts from and whose item does not file findings; a landing
whose recorded target does not carry the candidate's branch names both and
refuses, rather than merging nothing and reporting the item landed.

## Launch

There is no wire object. The sealed ticket is the assignment, and `dispatch`
is one lock over readiness, the minted attempt, the established workspace, and
one committed `launch` record: `host`, `verb`, `agent`, `model`, `effort`,
native `fields`, and the generated `prompt`. That prompt is the whole
child-facing instruction surface, so an orchestrator invokes the launch
verbatim and hand-adds nothing; a caller who lost it replays the same
`dispatch` call and is handed the committed launch back unchanged.

The prompt names, once each, what a child cannot derive: the applied skill's
resolved file, the ticket's absolute path inside the established workspace,
that workspace and the instruction to run from inside it, this host's
verified interpreter, the resolved pack craft, the artifact kind and its Lens
entry, the review lane's root ticket
path, the assigned name, the lease deadline, the filled filing and closing
commands, the craft's verification scope, what a report is expected to carry,
and that every check runs to completion in the turn it starts with an
explicit timeout longer than the check and any backgrounded command killed
once superseded. It teaches no verdict token and no filing taxonomy: a child
files evidence into one channel, never a disposition and never a heading of
the protocol's choosing. It names the one mechanism for entering the applied
skill — the host's Skill tool, with the whole prompt forwarded verbatim as
the arguments, so the skill's fork arrives holding the assignment and a
child already running as the skill works in place — and names no pack for
the child to resolve: it hands the craft path. The
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
the child computes it, and no command yet recomputes it.

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
The join reads the tree the item was executed in off the attempt. It
adjudicates nothing and binds no findings, accepted subset, or fixed
artifact identity of its own: the mechanical checker/repair selector that
used to do that on `--findings-file`/`--accepted-file`/`--artifact` retired
with the gate-stage ids -- `.gate.critique.<lens>`, `.gate.repair`, `.check`
-- it selected between, minted by no live command. A worker's own fixed
artifact identity reaches its ticket the same way any other closing fact
does: printed verbatim in the outcome evidence the launch prompt asks for,
never through a join flag.

`review_v1`, its `GatePlan`/`CritiqueAdjudication`/`RepairOutcome` chain,
`checked_by`/`review_stage`, and `check <run> <id> --stage <id>.check` --
the one surviving reader the gate-stage census above left standing -- are
themselves retired: no live command ever built the chain that reader required,
so its one input was hand-edited state, which the host block forbids. A
critique is a `judge` ticket and its repair a `do` ticket, sequenced by the
calling workflow's prose, and both return the ordinary way -- the
executor's `## Report` and the disposition this join records.

## Cutover

The public facade has no role-bearing `claim` route, no packet route, and no
dual reader. A claimed or suspended ticket without this record is
`claim-without-dispatch`: a live claim exists only as a dispatch-v1 attempt,
and the attempt's `owner` and `opened_at` are the lease — the ticket carries
no projection of them. History is never inferred or rewritten.

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
