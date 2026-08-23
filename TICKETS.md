# Tickets

How work moves through orchflows, for humans. This is the human
surface: nothing here is law, and every section links the file that
owns its facts — [contracts/work-item.md](contracts/work-item.md) owns
the shape, [rules/verification.md](rules/verification.md) owns review,
[docs/vocabulary.md](docs/vocabulary.md) owns the terms,
[scripts/tickets.py](scripts/tickets.py) is the command facade.

## One file is the whole work order

A ticket is one markdown file that is the complete delegation packet
for one job: the worker gets the file path and nothing else. What it
may know, touch, and must return is all inside. Tickets live in the
per-user state sink, outside every repository
([rules/visibility.md](rules/visibility.md) §6), which is why a fresh
context in any checkout resumes a run mid-flight.

    ┌─ 00-root.02.md ─────────────────────────────────────────────┐
    │ ---                                                         │
    │ id, run, status, admission (a hash receipt)                 │
    │ executor: orch-tdd        pack: orch-code-pack              │
    │ depends_on: [00-root.01]  <- graph edge                     │
    │ write_scope, mutations    <- what it MAY change             │
    │ excluded_actions          <- what it may NOT do             │
    │ bound: 45m                <- time budget                    │
    │ claimed_by / claimed_at / checked_by                        │
    │ ---                                                         │
    │ ## Objective         what to do                    ┐        │
    │ ## Fixed inputs      exact evidence, by identity   │ cut-   │
    │ ## Completion test   oracles that decide "done"    │ time   │
    │ ## Return fields     shape of the answer           ┘        │
    │ ## Result            ┐                                      │
    │ ## Verification      │ executor-written,                    │
    │ ## Feedback          │ streamed while the                   │
    │ ## Risks             │ work happens                         │
    │ ## Handoff           ┘                                      │
    └─────────────────────────────────────────────────────────────┘

The top four sections are the **cut** — authored by the planner,
frozen once anyone claims the ticket. The bottom five belong to the
executor, written as the work happens, never in one write at the end.
Field-by-field meaning: [contracts/work-item.md](contracts/work-item.md).

## A run is a directory of tickets

A delivery run holds one **root ticket** (the whole request, frozen by
`orch-spec`, cut by `orch-decompose`), the **unit tickets** cut from
it, and pre-issued **gate stubs** for the end-of-run review:

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

Two mechanisms, both in the frontmatter:

- **`depends_on`** is the dependency graph. A ticket is admitted only
  when every dependency is `complete`; `orch-frontier` dispatches every
  ticket whose dependencies are done, all in parallel — the rolling
  frontier, no phase barriers.
- **`cohort`** says who freezes together. A `v1:batch:` cohort freezes
  every member the moment any one is claimed; a `v1:root:` cohort
  freezes each member individually, so the planner keeps correcting
  pending units and adding new ones while their siblings run.

## Lifecycle

                admission graded,          a worker takes it,
                receipt stamped            receipt re-checked
     pending ─────────────────▶ ready ────────────────▶ claimed
        ▲                                                  │
        │ amend / recut                                    │ work,
        │ (pending/ready only,                             ▼ review
        │  and only unfrozen)                    join adjudicates
        │                                                  │
        └── stale claim sent back ◀───────┬────────────────┤
                                          │                ▼
                                     suspended    complete · blocked
                                                  stalled · limited
                                                  failed

**Admission** is the gate into work: `tickets.py` grades the ticket
against a snapshot of the whole run — dependencies complete, executor
bound by the stamped pack, workspace policy, inputs resolvable — and
stamps a hash **receipt** of the frozen cut. Claiming and packet
emission re-grade and refuse on a mismatched receipt: the worker is
provably executing the exact cut that was admitted. Corrections
(`amend`, `recut`) exist only before a claim; after it, the cut is a
fixed target ([rules/verification.md](rules/verification.md) §3).

## Review

Three moments, each a fresh reader who did not produce the thing
([rules/verification.md](rules/verification.md) §10–§11):

    decompose ─▶ CUT CHECK ─▶ units run ─▶ CHECK ─▶ RE-VERIFY ─▶ GATE
                 before any    parallel     fixes    read-only    critique
                 unit starts   frontier     in place              -> repair
                                                                  -> verify

1. **Cut check** — before any unit is dispatched, a checker reads the
   issued ticket set as data, corrects it with `amend`/`new`, and is
   accepted when [scripts/cutcheck.py](scripts/cutcheck.py) exits 0.
   Once a unit is claimed, cut correction is refused.
2. **Unit check** — after the executor finishes under its claim,
   `orch-critique` reviews the result against the ticket's own
   completion test with the same write scope, fixes what it finds, and
   records the pass. Skipped when every criterion predates the work
   (`provenance: pre-existing` — the test is already independent) or
   when the ticket defers independence to the gate.
3. **Re-verification** — `orch-verify`, with no write authority,
   re-runs the completion test at the recorded result identity and
   files `## Verification` only.

Last, the **composite gate** runs over the integrated whole: critique
lenses find defects, `orch-repair` fixes the accepted blocking ones,
verify re-runs the oracles.

## Errors and feedback

- **Refusals are named, never silent.** A command that cannot proceed
  returns a structured finding — `dependency-incomplete`,
  `executor-pack-mismatch`, a stale receipt — instead of doing
  something approximate.
- **The join rules on everything.** No returned result is trusted until
  `orch-integrate` adjudicates it, and only the join sets terminal
  status ([rules/delegation.md](rules/delegation.md)). A worker cannot
  declare itself done.
- **Silence is explicit.** Findings go to `## Feedback`, hazards to
  `## Risks`; `[]` fills an empty section so nothing is ambiguous.
  Hitting an excluded action means suspending with a `## Handoff` that
  a fresh context can resume from, not improvising.
- **Claims go stale.** Each ticket carries a `bound`; a claim past it
  with no motion is sent back to `pending` and recut before reclaim.
- **Findings fork by severity.** Blocking defects go to `orch-repair`;
  non-blocking ones are recorded as candidate scope for a later pass —
  logged, never dropped.

The through-line: authority, evidence, the definition of done, the
answer, and the review trail live in one file, and receipts plus
fresh readers keep any of it from moving while someone works against
it.
