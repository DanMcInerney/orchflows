# Successors from the trunk-defects run

Written 2026-09-04 at the close of run `20260904T034500Z-trunk-defects`,
frame `B1`, merged as [PR #174](https://github.com/DanMcInerney/orchflows/pull/174)
(`main` b2bf316b, CI 6/6) and installed. Nothing here blocks anything.

The run itself is done: four defects fixed, one judge over the joined tip,
one bounded repair, gate green, library reinstalled, and every ticket in
both this run and `20260903T155153Z-library-cleanup` settled terminal.

## Two corrections to what the spec says

**`tools/run_serial_compat.py` grew, it did not shrink.** U3's report
claimed 519 → 514 lines; the tree says 519 → **523**. The sentinel-prune
logic is larger than the two derived comparisons it removed. So the
spec's section 6 deferral and its decision 7 both now cite a wrong number,
and the file sits further over the 500-line presumption than before, not
closer. Nothing splits it.

**U1 does not heal historical tickets, and was never going to.** It is
tempting to read decision 1 as retroactive — the seal now reads the fields
a ticket *carries*, so a ticket carrying `independence` should re-derive
its old digest. It does not. The pre-cleanup roster sealed exactly
`{bound, independence, isolation}`; U1's complement seals those plus `run`,
`pack`, `pack_digest`, `parent` and `done`. Measured on `B1.11`: the
installed trunk still refuses `assignment-mismatch`. U1 prevents the *next*
wedge of that shape; it cannot open the last one. The recovery stays
`git archive <base> scripts` into a temporary directory, which this run
exercised end to end and which works.

## Carried from the judgement

`research/trunk-defects-judgement-2026-09-04.json` is the record.

- **F2, a predicate that cannot run.** U2's `retired -> True` short-circuit
  leaves `status_ownership_returned`'s trailing `all(kind == "lifecycle")`
  unreachable: a lone attempt is either live or retired, since `replaced`
  always appends a second. Mutating the tail to `return False` leaves 119
  tests green with an identical control. The implementation matches the
  spec's section 2 shape exactly, so removing the tail would reverse a
  closed decision — a planner's call, not a repair.
- **The other blind sibling.** `SavedWorkflowShapeTest`
  (`tests/test_ticket_frames.py:710`) still globs `example-workflows/` only,
  the same gap F3 named and B1.6 fixed for `FrameLawOwnerTest`. Green
  today because both `skills/workflows/` bodies name `--workflow`; it is an
  uncovered directory rather than a defect.

## The flake, diagnosed but not fixed

Four independent readers — U2, U3, U4 and this driver — hit a
non-reproducible `run_required.py` exit 1 on a tree that then passed. Two
failures and three passes were measured at one tree identity
(`d997a9653366`), and `tools/run_tests.py` standalone was green there.

The mechanism is `tools/run_tests.py:278`: a module's test child passes
every test, then its *process* exits non-zero, so `ok` flips to False and
`report()` returns 1 while the per-module failure and error counts stay 0.
On Windows that shape is a crash during interpreter shutdown — a lingering
thread or a temp-dir cleanup race. `tests.test_workspace` is the heaviest
module at ~138s. The crash itself is undiagnosed.

Two things make it worse than it needs to be, and both are fixable:

- **A red run reports a green summary line.** The totals are summed from
  per-module counts, so a run killed by `child exited N after reporting
  success` prints `0 failures, 0 errors` beside exit 1. A reader who greps
  the summary sees green.
- **Nothing persists the evidence.** The friction all three children logged
  said the runners keep no per-leg log. That is wrong in both halves:
  `tools/run_required.py:206` emits every leg's captured output before the
  exit column, and `run_tests.py:313` prints a `FAILED MODULE` block with
  the child's whole output plus a `FAILED: <module>` line. The real gap is
  narrower — neither writes that output to a file, so an intermittent
  failure seen once cannot be re-read after the process exits. Four
  consecutive readers tailed it away instead, which is what made it look
  undiagnosable.

## What the armed repair door leaves behind

A `done` that fails at `land` mints a repair ticket in `status: ready`. If
the failure was a flake and the re-land succeeds, that ticket is never
launched and never graded, and it blocks `frame-close` until a driver
settles it by hand. Both runs produced one (`B1.2.repair.1` here,
`B1.3.repair.1` in the cleanup run). Worth deciding whether the door should
arm lazily, or whether a re-land that succeeds should retire the repair it
armed.

Related: the previous handoff named eight wedged tickets in the cleanup
run; there were **ten**. `B1.3.repair.1` and `B1.8` were also non-terminal
and are settled now.

## Still unowned from the cleanup run

`research/HANDOFF-trunk-defects.md`'s successor section is unchanged and
still accurate: `reader/` sitting outside every required check, no committed
check grading a citation into another file's prose, `DOCUMENTED_PATH_RE`
being blind to a path inside a backticked command, `sheets/` outside
`LINKED_MD_ROOTS`, and the retired workflow names still live behind the
pinned `reader/web/src` dist.
