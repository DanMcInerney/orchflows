# Worklog contract

The run's persistent state file: what makes fresh-context iteration,
resumption, and post-hoc improvement possible. One per run, at
`<state-root>/runs/<run>/worklog.md`, where the state root is the
user-scope sink `scripts/state_root.py` resolves — one per user, outside
every repository. Iterations read it instead of transcripts; transcripts
are never state.

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

Beside it, `<state-root>/runs/<run>/run.json` — the run's identity, written
on the run's first state write, appended to and never rewritten:

- `run` — the run id; equals the name of the directory holding this file.
- `sink_convention` — integer: the sink layout this record was written under.
- `opened_at` — when the run's first write landed; never rewritten.
- `project` — which project owns this run id; never rewritten once set.
  `project.root` — absolute path of the **main** checkout, a linked worktree
  resolved to it and a submodule to its superproject; `project.origin` — the
  origin url, null when the repository has no remote; `project.name` — the
  root's base name, a human label, never compared.
- `workspaces` — every workspace that has written to this run, in first-write
  order. `workspaces[].path` — that workspace itself, **not** its main
  checkout; `workspaces[].first_seen` — when its first write landed.
