# Tickets

How work moves through orchflows, for humans. This is the human
surface: nothing here is law, and every section links the file that
owns its facts — [contracts/work-item.md](contracts/work-item.md) owns
the shape, [rules/verification.md](rules/verification.md) owns review,
[docs/vocabulary.md](docs/vocabulary.md) owns the terms,
[scripts/tickets.py](scripts/tickets.py) is the command facade.

## One file is the whole work order

A ticket is one markdown file holding the durable assignment, lifecycle,
result, and verification truth for one job. A role-bearing child is pointed at
this file by its launch prompt, and reads it whole. Tickets live in the
per-user state sink, outside every repository
([rules/visibility.md](rules/visibility.md) §6), which is why a fresh
context in any checkout resumes a run mid-flight.

    ┌─ B1.2.md ───────────────────────────────────────────────────┐
    │ ---                                                         │
    │ id, run, status, admission, dispatch_v1                    │
    │ executor: orch-do        pack: orch-code-pack              │
    │ parent: B1                <- the call edge                  │
    │ depends_on: [B1.1]        <- optional graph edge            │
    │ bound: 45m                <- time budget                    │
    │ (the claim lease lives in dispatch_v1, not here)            │
    │ ---                                                         │
    │ ## Goal              observable result             ┐        │
    │ ## Context           facts and constraints          │ seal   │
    │ ## Details           optional planner guidance     ┘        │
    │ ## Report            executor-written, streamed while       │
    │                      the work happens                       │
    └─────────────────────────────────────────────────────────────┘

The semantic assignment is sealed before dispatch. A later semantic change
opens a successor run whose root Context cites the accepted predecessor result;
it never rewrites this run or invents an in-run root generation. The result sections belong to the
executor, written as the work happens, never in one write at the end.
Field-by-field meaning: [contracts/work-item.md](contracts/work-item.md).

Before issue, `tickets.py lint <run> [<id>] --file <path>` grades a
hand-authored ticket file's exact pre-issue shape without writing it anywhere.
After issue, `tickets.py show <run> <id>` inspects one ticket's parsed identity
and sections without mutation.

## Dispatch protocol

`orchflows.dispatch.v1` makes the ticket the fence around at-least-once agent
delivery. The caller invokes one door — `tickets.py do` or `judge` for a
brick, `tickets.py dispatch` for a ticket written by hand — which promotes
readiness, establishes the workspace, opens one attempt, and commits one
immutable `launch` atomically — the agent, model, effort, and the whole
prompt the child is given, so the caller invokes a `launch` object rather than
transcribing a model, an agent, or a set of instructions by hand. That prompt
also tells the child to commit inside its candidate before closing and to
print one verbatim `artifact: <kind>:<identity>` line — `findings: <path>`
too, from a judging lane — so the parent relays a machine line instead of a
paraphrase. The granular
`dispatch-open`, `dispatch-retire`, and `dispatch-replace` operations remain
public for recovery, and replaying the same `dispatch` call — or the same
`do` — hands back the same launch. There is no
accept step: the child's first filed record is its acceptance, and every record
it files carries the attempt's dispatch id, seal, and owner.

The assignment seal identifies semantic generation. The dispatch id identifies
one attempt and remains fixed across exact delivery retries. Transport silence
replays the stored launch to the same child; it never creates a second live
child. Retirement precedes replacement, and `dispatch-replace` performs both
sides atomically. The attempt reserves one `outcome` identity. The
child commits its unstreamed closing evidence delta with `dispatch-outcome`.
The join consumes only that durable outcome, so recovery never guesses
which streamed write closed the attempt. Fixed record ids replay identically
and conflicting or unseen stale traffic refuses.

`tickets.py land` is the return in one command: it imports the outcome, joins
it, retires the derived worktree, and reports the frontier that join made
ready — one lock around all three, and it says which steps it found already
done. `dispatch-outcome` and `dispatch-join` remain public for recovery.

A launch prompt names its ticket and never copies it, so the sink is always the
authority a child reads its assignment from. A claimed ticket without an attempt refuses
`claim-without-dispatch`: a live claim exists only as a dispatch-v1 attempt,
whose owner and opened time are the lease. The normative shapes and precedence live in
[contracts/dispatch.md](contracts/dispatch.md).

## A run is a tree of tickets

A delivery run holds one **root ticket** for the whole request. A direct
root binds its complete work to one executor. Anything larger opens a
**frame** — one ticket per workflow invocation, holding the journal its
driver writes and re-reads — and hangs its bricks underneath:

    <state sink>/tickets/<run>/
    ├── 00-root.md          the whole job
    ├── B1.md               a frame: goal, journal, no executor, no pack
    ├── B1.1.md   ┐
    ├── B1.2.md   │ bricks, one bounded work item each, minted under B1
    └── B1.3.md   ┘

The `parent` field is what places each one, so the ticket tree is the call
tree — and a fresh context reads the tree instead of reconstructing the
call stack. Cut shape — what a unit may be, who owns what — is
[rules/topology.md](rules/topology.md)'s.

## How tickets relate

The frontmatter carries three related mechanisms:

- **`parent`** is the call edge. A brick minted at runtime hangs under the
  frame or root that opened it, takes an auto-minted `<parent>.<n>` id, and
  seals through that parent's own generation rather than through a cut that
  closed before it existed.
- **`depends_on`** is the dependency graph, for tickets issued together. A
  ticket is admitted only once
  every dependency has landed a report — `complete`, or `limited` where the
  work stopped short but still delivered one; `blocked` and `failed` do not
  satisfy it. `tickets.py land` prints every
  ticket whose dependencies are done, and they go out in parallel — the
  rolling frontier, no phase barriers. A runtime child declares none: the
  calling prose is what orders it.
- **`root_generation`, `cut_generation`, and `assignment_seal`** bind every
  member to one validated immutable snapshot. Deterministic cut correction
  happens
  before seal; a sealed semantic change uses a successor run. A stale or
  mismatched seal is never dispatched.

## Lifecycle

                admission graded       dispatch-open commits
                and seal checked       one absolute lease
     pending ─────────────────▶ ready ────────────────▶ claimed
                                                           │ outcome,
                                                           ▼ join
                                                    tickets.py land
                                                           │
                                               ┌───────────────────┤
                                               ▼                   ▼
                                        suspended       complete · blocked
                                                         stalled · limited · failed

**Admission** is the door into work: `tickets.py` grades the ticket
against a snapshot of the whole run — dependencies complete, executor
bound by the stamped pack, workspace policy, inputs resolvable, and for a
runtime child its parent's own seal — and
stamps a hash **receipt**. `dispatch-open` atomically records
the claim and absolute lease, and the launch is committed
against that same seal. After an
attempt opens, the assignment is a fixed target
([rules/verification.md](rules/verification.md) §3).
Every joined disposition retires the attempt. A suspended ticket retains its
claimant observations and its `## Report`, but it has no live attempt.

## Review

Three moments use readers who did not produce the fixed artifact
([rules/verification.md](rules/verification.md) §7):

    plan ─▶ CUT CHECK ─▶ bricks under the frame ─▶ JUDGE ─▶ LAND
            before units       one outside path     a brick,   runs the
                                                    then a do  done
                                                    to repair  predicate

1. **Cut check** — before any unit is dispatched, a checker reads the
   issued ticket set as data and returns blockers to the planner before a
   replacement generation is sealed. It is
   accepted when [scripts/cutcheck.py](scripts/cutcheck.py) exits 0.
   Once a unit dispatch opens, cut correction is refused.
2. **Ticket independence** — the caller's own join (`tickets.py land`) reads
   Goal and Context against the fixed artifact and evidence; that is now
   the ordinary outside-independence path's one shape. The distinct
   `<id>.check` review ticket, its `orch-judge` dispatch, and `tickets.py
   check <run> <id> --stage <id>.check`'s anchor onto `checked_by` retired:
   no live door ever built the ledger that reader required.
3. **Critique and repair** — a critique is a `judge` brick over the artifacts
   it is handed and the repair answering it a `do` brick, sequenced by the
   calling workflow's prose; no door emits a lensed family for either, and
   each returns the ordinary way — the executor's `## Report` and the
   joined disposition `land` records. Closing a frame over two or more `do`
   children refuses unless the tree holds a judging child or the journal
   says `unjudged: <reason>`.

## Errors and feedback

- **Refusals are named, never silent.** The dispatch protocol documents
  `state-inaccessible`, `stale-attempt`, `live-attempt`, `identity-mismatch`,
  `assignment-mismatch`, `dispatch-mismatch`, `claim-without-dispatch`,
  `dispatch-record-invalid`, and
  `idempotency-conflict`. Other command families expose their closed codes in
  `--help` and their owning contracts instead of doing something approximate.
- **The join rules on everything.** No returned result is trusted until
  `tickets.py land` adjudicates it. For v1, only the join sets suspended or terminal
  status ([rules/delegation.md](rules/delegation.md)). A worker cannot
  declare itself done.
- **Structure only where a machine reads it.** Nothing on the return side is
  machine-parsed any more: a critique's findings live in its own `## Report`,
  like anything else a child has to say, in whatever form it judges useful.
  Work that cannot finish within its bound suspends through the join,
  reporting what a resumer needs rather than improvising.
- **The absolute lease does not move.** Launch replay, transport activity, and
  result filing never extend `lease_expires_at`. An ended attempt must be
  retired or atomically replaced before a successor runs. Suspension leaves a
  retired attempt, never a live predecessor.
- **Findings fork by severity.** Blocking defects go to a `do` repair brick;
  non-blocking ones are recorded as candidate scope for a later pass —
  logged, never dropped.

The through-line: authority, evidence, the definition of done, the
answer, and the review trail live in one file, and receipts plus
fresh readers keep any of it from moving while someone works against
it.
