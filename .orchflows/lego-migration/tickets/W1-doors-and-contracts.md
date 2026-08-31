# W1 — doors-and-contracts (wave 1, serial, worker: opus)

## Goal

Bricks have one door and tickets have parents. `tickets.py do <run>
--pack P --goal-file F [--details-file D] [--parent ID] [--done JSON]
[--isolation …] [--bound …] [--host H]` and the twin `judge <run>
--pack P --goal-file F --artifacts LINES [--parent ID] …` each perform,
under one lock: mint an auto id under the parent (`<parent>.<n>`, root
ids `B<n>` when parentless), write the Goal/Context/Details ticket,
seal it bound through its parent's sealed generation (the loop-round
admission pattern generalized: every runtime child is self-sealed and
verified through the sealed parent — the sealed-CUT membership check
retires), pin the pack digest, open the attempt with an absolute lease,
establish per the adapter, and emit the launch. The generated prompt
additionally carries: an explicit "commit your work in the candidate
before closing; the closing note names the commit" line (two of four
workers skipped the commit on 2026-08-31); a typed artifact return line
the child must print verbatim (`artifact: git:<full-sha>` |
`doc:<path@sha256-digest>` | `evidence:<store-id>`, chosen by the
pack's adapter); and, for judge, `findings: <path>` as a second
verbatim machine line. `land` accepts the typed line for non-git
adapters wherever it accepted `git:` identities.

## Context

- owners: `scripts/tickets_dispatch_facade.py`, `tickets_assignment.py`
  (prompt), `tickets_generations.py` (seal), `tickets_admission.py`
  (the seal-through-parent branch already exists for loop rounds —
  generalize, don't duplicate), `tickets_format.py` (id grammar owner),
  `contracts/work-item.md` + `contracts/shapes.json` (`parent` field;
  drop `depends_on` requirement to optional — prose order replaces
  edges for runtime children), `contracts/dispatch.md` (typed artifact
  identities)
- this ticket is the SOLE owner of contracts/shapes changes in its
  wave; W2 builds on your tip
- keep `dispatch`/`land` working unchanged for existing tickets — W3
  deletes the old doors; you only ADD the folded ones

## Details

- The one-door fold reuses stamp/validate/seal internals as private
  functions; do not delete the public doors yet (W3's job) — evidence:
  deletion-first is per-surface, and the example workflows still ride
  the old doors until W3 converts them.
- `--done` takes the existing done-binding JSON grammar unchanged.
- Auto-id collision under concurrent minting: the run lock you already
  hold at the door is the arbiter; prove with a test that two
  concurrent `do` calls under one parent mint distinct ids.
- Typed lines: the adapter table (`tickets_adapters.ADAPTER_REGISTRY`)
  gains one field naming the artifact identity kind; `doc:` digests are
  sha256 over the document bytes at close, computed by the child per
  the prompt's instruction, verified nowhere yet (W-future; say so in
  the contract as "declared, not verified").
- Non-scope: frames (W2a), renames (W2b), any deletion (W3/W4).
- Done: gate + preflight plainly green; a temp-sink test drives
  `do` end-to-end (mint→launch emitted with all three new prompt
  lines→result→outcome→land) for a git pack AND a document-tree pack;
  T0 records + re-pin; serial manifest regenerated last.
- Report: commits; the full generated prompt for one `do` verbatim;
  the id grammar as landed; which admission code path retired.

## Report
