# Worklog contract

The run's persistent state file: what makes fresh-context iteration,
resumption, and post-hoc improvement possible. One per run, at
`<main-repository-root>/.orch/runs/<run>/worklog.md`, where the main
repository root is the shared root a linked worktree's `.git` pointer
resolves to — never the worktree's own root. Iterations read it instead
of transcripts; transcripts are never state.

- `goal` — the frozen objective and acceptance — or the done-check for
  a loop run — verbatim; never edited after iteration 1.
- `spec` — path to the stamped spec; `tickets` — path to the run's ticket
  directory.
- `iterations` — one entry per pass: what ran, verdicts by identity,
  budget spent.
- `blame_classes` — one entry per failed join: the blame class and the
  owner it routes to, per the delegation contract.
- `failed_approaches` — every approach that did not work, with the
  evidence that killed it; an iteration never re-walks an entry here.
- `queued_scope` — discovered work outside the frozen goal; queued, never
  merged into the live goal.
- `terminal` — empty until the run exits, then exactly one of: `complete`
  | `blocked` | `stalled` | `limited` | `failed`, with the deciding
  evidence. A parked-only pause is not an exit: `terminal` stays empty
  and the run resumes from its tickets. Parked is not in progress: no
  item is under way, and the pause names the external action awaited
  and every item queued behind it.

Notes append in occurrence order, and no note is written past a terminal
section: a worklog carries no terminal placeholder until it closes.
Writing an artifact that already exists is refused by default, the
refusal naming the existing path.
