# W2a — frames-and-resume (wave 2, parallel with W2b, worker: opus)

## Goal

The durable call stack exists. `tickets.py frame-open <run> --goal-file
F [--parent ID]` mints a pack-less frame ticket (sealed goal, parent
link, journal = its Report; opening with no run mints the run);
`tickets.py frame-close <run> <id> [--status S] [--done JSON]` is the
recording act and REFUSES over two or more do-children unless the
subtree holds a judge child or the journal carries an
`unjudged: <reason>` line (design amendment A2); journal appends ride
the existing `result` door with the frame's own identity.
`orchflows resume` lists this project's open frames — goal first line,
age, journal present/absent, open children, live leases — pull-based,
newest first, nothing resident.

## Context

- owners: new `scripts/tickets_frame.py` (small; reuse W1's private
  fold internals for open), `scripts/orchflows.py` (resume subcommand),
  `scripts/tickets_format.py` (frame recognition: pack-less + a
  `frame: true` marker W1's shapes already… if W1 did not add one, add
  it with its own T0 record — coordinate by reading W1's landed diff
  first; you branch from W1's tip)
- design: `research/lego-design-2026-08-31.md` §Frames + amendments
  A1 (the journal is the driver's working memory — resume and the
  frame docs both say waves BEGIN by re-reading it) and A2
- frames carry no lease and no pack (design A7); land's not-isolated
  path is the close's shape

## Details

- The A2 check counts do-children by parent link + executor, judge
  children by executor; `unjudged:` is matched as a journal line
  prefix — one grammar owner in tickets_format beside the id grammar.
- resume reads the sink only (tickets + run.json project binding);
  filter to the invoking project by the same `_same_project` law the
  admission uses; show cross-worktree runs of this project.
- Non-scope: no deletions, no renames, no doc sweeps beyond the
  docstrings you own.
- Done: gate + preflight green; temp-sink test drives
  frame-open → two `do` children → close REFUSED → judge child →
  close lands (and the `unjudged:` alternative); a resume listing
  asserted verbatim; manifest last.
- Report: commits; one resume listing verbatim; the A2 refusal text
  verbatim; what frame recognition looks like in the shapes.

## Report
