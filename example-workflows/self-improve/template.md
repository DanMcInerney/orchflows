---
name: self-improve
description: Mine the state sink's friction and run evidence into one qualified proposal and land it in its owner. Use on demand or closing a run.
entry: named
placeholders: [window, workspace, run]
---

The improvement loop of [rules/improvement.md](../../rules/improvement.md)
as one run: the sink's evidence for a window becomes ranked proposals, and
the top-ranked proposal becomes a root ticket whose cut, gate and join land
it in its owner and record the coverage that stops the same evidence
requalifying.

`01-deliver` is a root ticket whose gate verifies the landing.

Instantiate with two: `window`, the sessions, runs, projects, or period
the cycle mines, and `workspace`, the repository holding the proposal's
causal owner — `01-deliver`'s candidate workspace; `00-mine` is read-only. The
third, `run`, is `instantiate`'s own and takes no `--set`: `01-deliver`
cites `00-mine`'s Result by identity, and an identity naming a ticket
names the run it is in.
