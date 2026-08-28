# Tickets

How work moves through orchflows, for humans. This is the human
surface: nothing here is law, and every section links the file that
owns its facts — [contracts/work-item.md](contracts/work-item.md) owns
the shape, [rules/verification.md](rules/verification.md) owns review,
[docs/vocabulary.md](docs/vocabulary.md) owns the terms,
[scripts/tickets.py](scripts/tickets.py) is the command facade.

## One file is the whole work order

A ticket is one markdown file holding the durable assignment, lifecycle,
result, and verification truth for one job. A role-bearing child receives a
committed packet projection, not merely this file path. Tickets live in the
per-user state sink, outside every repository
([rules/visibility.md](rules/visibility.md) §6), which is why a fresh
context in any checkout resumes a run mid-flight.

    ┌─ 00-root.02.md ─────────────────────────────────────────────┐
    │ ---                                                         │
    │ id, run, status, admission, dispatch_v1                    │
    │ executor: orch-tdd        pack: orch-code-pack              │
    │ depends_on: [00-root.01]  <- graph edge                     │
    │ bound: 45m                <- time budget                    │
    │ claimed_by / claimed_at / checked_by                        │
    │ ---                                                         │
    │ ## Goal              observable result             ┐        │
    │ ## Context           facts and constraints          │ seal   │
    │ ## Suggested files  optional, non-binding          ┘        │
    │ ## Result            ┐                                      │
    │ ## Verification      │ executor-written,                    │
    │ ## Feedback          │ streamed while the                   │
    │ ## Risks             │ work happens                         │
    │ ## Handoff           ┘                                      │
    └─────────────────────────────────────────────────────────────┘

The semantic assignment is sealed before dispatch. A later semantic change
opens a successor run whose root Context cites the accepted predecessor result;
it never rewrites this run or invents an in-run root generation. The result sections belong to the
executor, written as the work happens, never in one write at the end.
Field-by-field meaning: [contracts/work-item.md](contracts/work-item.md).

Before issue, `tickets.py lint <run> [<id>] --file <path>` grades the exact
candidate that `tickets.py new <run> [<id>] --file <path>` would project.
After issue, `tickets.py show <run> <id>` inspects one ticket's parsed identity
and sections without mutation.

## Dispatch protocol

`orchflows.dispatch.v1` makes the ticket the fence around at-least-once agent
delivery. The caller promotes readiness, opens one attempt with
`dispatch-open`, and commits its immutable reference or inline projection with
`dispatch-packet`. Pass the response `.packet` value—not the response wrapper
or a reconstructed shell literal—to `dispatch-receive` through `--file <path>`
or UTF-8 standard input with `--file -`. The established child supplies its
actual assigned name, role, profile, reply target, and workspace authority;
only a durable accepted receipt permits the exact named executor to run.

The assignment seal identifies semantic generation. The dispatch id identifies
one attempt and remains fixed across exact delivery retries. Transport silence
replays the stored projection to the same child; it never creates a second live
child. Retirement precedes replacement, and `dispatch-replace` performs both
sides atomically. The packet carries one reserved `outcome` identity. The
child commits its unstreamed closing evidence delta with `dispatch-outcome`.
`dispatch-join` consumes only that durable outcome after the committed
`dispatch-receipt`, so recovery never guesses
which streamed write closed the attempt. Fixed record ids replay identically
and conflicting or unseen stale traffic refuses.

Reference packets are normal. Inline packets carry the sealed ticket snapshot,
but the authoritative sink must still authenticate receipt; self-carried
offline material cannot authorize role-bearing execution. A ticket projection
cannot be downgraded to ephemeral. A pre-v1 live claim without an attempt refuses
`legacy-live-claim`: its existing owner must complete or abandon it before v1
installation. The normative shapes and precedence live in
[contracts/dispatch.md](contracts/dispatch.md).

## A run is a directory of tickets

A delivery run holds one **root ticket** for the whole request. A direct
root binds its complete work to one executor. A genuinely decomposed root is
frozen by `orch-spec`, cut by `orch-decompose`, and joined by pre-issued
**gate stubs** for the end-of-run review:

    <state sink>/tickets/<run>/
    ├── 00-root.md                     the whole job
    ├── 00-root.01.md   ┐
    ├── 00-root.02.md   │ unit tickets, one bounded work item each
    ├── 00-root.03.md   ┘
    ├── 00-root.gate.critique.code.md  ┐
    ├── 00-root.gate.repair.md         │ the composite gate, run last
    └── 00-root.gate.verify.md         ┘

Cut shape — what a unit may be, who owns what — is
[rules/topology.md](rules/topology.md)'s.

## How tickets relate

The frontmatter carries two related mechanisms:

- **`depends_on`** is the dependency graph. A ticket is admitted only
  when every dependency is `complete`; `orch-frontier` dispatches every
  ticket whose dependencies are done, all in parallel — the rolling
  frontier, no phase barriers.
- **`root_generation`, `cut_generation`, and `assignment_seal`** bind every
  member to one validated immutable snapshot. Direct and decomposed roots use
  the same generation and seal commands. Deterministic cut correction happens
  before seal; a sealed semantic change uses a successor run. A stale or
  mismatched seal is never dispatched.

## Lifecycle

                admission graded       dispatch-open commits
                and seal checked       one absolute lease
     pending ─────────────────▶ ready ────────────────▶ claimed
                                                           │ outcome,
                                                           ▼ join
                                                     dispatch-join
                                                           │
                                               ┌───────────────────┤
                                               ▼                   ▼
                                        suspended       complete · blocked
                                                         stalled · limited · failed

**Admission** is the gate into work: `tickets.py` grades the ticket
against a snapshot of the whole run — dependencies complete, executor
bound by the stamped pack, workspace policy, inputs resolvable — and
stamps a hash **receipt** of the frozen cut. `dispatch-open` atomically records
the claim and absolute lease. `dispatch-packet` commits the delivery projection;
`dispatch-receive` re-grades its seal and actual receiver authority. After an
attempt opens, the assignment is a fixed target
([rules/verification.md](rules/verification.md) §3).
Every joined disposition retires the attempt. A suspended ticket retains its
claimant observations and `## Handoff`, but it has no live attempt.

## Review

Three moments use readers who did not produce the fixed artifact
([rules/verification.md](rules/verification.md) §7):

    decompose ─▶ CUT CHECK ─▶ rolling frontier ─▶ GATE
                 before units      one outside path    critique
                                                      -> repair
                                                      -> verify

1. **Cut check** — before any unit is dispatched, a checker reads the
   issued ticket set as data and returns blockers to the decomposer before a
   replacement generation is sealed. It is
   accepted when [scripts/cutcheck.py](scripts/cutcheck.py) exits 0.
   Once a unit dispatch opens, cut correction is refused.
2. **Ticket independence** — each result takes one outside-independence path:
   either the ordinary durable evaluator/adjudication carrier or the downstream
   composite gate. Both use fresh read-only `orch-critique`; neither repairs
   its own target. `tickets.py checker-stage <run> <id>` derives one explicit
   `<id>.check` review ticket from the sealed target. That stage uses the same
   `dispatch-packet` → accepted `dispatch-receive` → `dispatch-outcome` →
   `dispatch-join` carrier as every role-bearing execution. Only
   `tickets.py check <run> <id> --stage <id>.check` may attach the joined,
   identity-anchored adjudication to `checked_by`; callers cannot write trusted
   findings directly.
3. **Composite gate** — `GatePlan` fixes the resolvable integrated artifact,
   normalized established workspace, root pack, isolation `none`, and stable ordered lens
   identities. Independent critiques remain parallel. `CritiqueAdjudication`
   binds the full findings and accepted blocker set; `RepairOutcome` binds the
   repaired identity or proves that set empty; fresh `Verification` evaluates
   exactly that predecessor identity. Each append-only stage names the prior
   stage digest, forming one predecessor-linked `orchflows.review.v1` chain.

## Errors and feedback

- **Refusals are named, never silent.** Packet receipt documents
  `packet-invalid`, `state-inaccessible`, `assignment-divergent`,
  `stale-attempt`, `identity-mismatch`, `role-mismatch`, `profile-mismatch`,
  `authority-mismatch`, `dispatch-mismatch`, `dispatch-record-invalid`, and
  `idempotency-conflict`; unseen execution records additionally refuse
  `receipt-required`. Other command families expose their closed codes in
  `--help` and their owning contracts instead of doing something approximate.
- **The join rules on everything.** No returned result is trusted until
  `orch-integrate` adjudicates it. For v1, only `dispatch-join` sets suspended or terminal
  status ([rules/delegation.md](rules/delegation.md)). A worker cannot
  declare itself done.
- **Silence is explicit.** Findings go to `## Feedback`, hazards to
  `## Risks`; `[]` fills an empty section so nothing is ambiguous.
  Work that cannot finish within its bound suspends through the join with a
  concise `## Handoff` rather than improvising.
- **The absolute lease does not move.** Packet replay, transport activity, and
  result filing never extend `lease_expires_at`. An ended attempt must be
  retired or atomically replaced before a successor runs. Suspension leaves a
  retired attempt, never a live predecessor.
- **Findings fork by severity.** Blocking defects go to `orch-repair`;
  non-blocking ones are recorded as candidate scope for a later pass —
  logged, never dropped.

The through-line: authority, evidence, the definition of done, the
answer, and the review trail live in one file, and receipts plus
fresh readers keep any of it from moving while someone works against
it.
