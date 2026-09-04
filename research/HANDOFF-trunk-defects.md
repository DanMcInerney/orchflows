# Handoff: finish the library cleanup, then run the trunk defects

Written 2026-09-03 at the end of run `20260903T155153Z-library-cleanup`.
Two pieces of work are queued: a pull request waiting on a human merge, and
a specified four-unit run waiting on a session to drive it. Do them in that
order; the second one patches files the first one changed.

## Where everything is

| thing | where | state |
|---|---|---|
| library cleanup | branch `claude/library-cleanup`, pushed, tip `c6bc9d39` | PR #173 open, CI 6/6, mergeable, **not merged** |
| trunk-defects spec | branch `claude/trunk-defects-spec`, local only, tip `f634f1f0` | committed, not pushed, no PR |
| installed library | `~/.orchflows`, receipt `c6bc9d39` | current with the PR head |
| frame `B1` | run `20260903T155153Z-library-cleanup` | closed complete, gate exit 0 |

The spec branch sits on top of `c6bc9d39`, so it carries the cleanup as
well. It was deliberately split off `claude/library-cleanup` so PR #173
stays exactly as it was reviewed.

## Step 1 — merge PR #173

https://github.com/DanMcInerney/orchflows/pull/173 — 389 files, +4,602 /
−23,911, CI green on all six jobs.

Merge it yourself in the GitHub UI, or with `gh pr merge 173 --merge`.
**Do not pass `--auto`.** This repo has no required checks, so `--auto`
merges immediately rather than waiting, and has put a red commit on `main`
before.

After the merge:

    git checkout main && git pull
    uv run --no-project python install.py --accepted-source <the merged commit>
    orchflows sync && orchflows list

`install.py` refuses a mutating install that does not name the commit its
gate accepted; that flag is not optional any more.

## Step 2 — run the trunk defects

Spec of record: `research/trunk-defects-spec-2026-09-03.md`. Driver:
`research/trunk-defects-tickets/RUN.md`. Four units, four defects the
cleanup run walked into and paid for in hours:

- **U1** the assignment seal reads the ticket instead of a code roster, so
  deleting a frontmatter field can no longer invalidate every open ticket.
- **U2** a retired attempt returns the ticket's status, so a child you stop
  can be settled instead of staying `claimed` forever.
- **U3** the serial manifest drops the two derived scalars that every pair
  of concurrent units collides on.
- **U4** the frame law becomes the one owner of the judgment cadence: judge
  once, over the joined tip, after the last wave.

Start a fresh session in a worktree off the merged `main` (or off
`c6bc9d39` if you would rather not wait for the merge) and hand it the
driver. Suggested branch `claude/trunk-defects`.

Three things the driver says that are easy to skip:

1. **Do not reinstall while that frame is open.** U1 changes the seal
   algebra. Installing it mid-run recomputes every open ticket's digest and
   refuses every further write with `assignment-mismatch`, which is the
   exact defect U1 exists to remove. Reinstall after `frame-close`.
2. Wave 1 is U3 alone. Every other unit adds a check, every added check
   regenerates the manifest, and U3 is what makes those regenerations merge
   cleanly.
3. One judge, after the last wave, over the joined tip. Not one per unit.

## Step 3 — clean up the wedged tickets

Once U2 has landed and been installed, eight tickets in the cleanup run can
finally be settled. They are `B1.10` and `B1.11` (a judge and a repair
stopped mid-flight) and `B1.15` through `B1.20` (six per-unit judges
abandoned when the cadence changed). For each:

    tickets.py dispatch-retire <run> <id> --assignment-seal <seal> --dispatch-id <id>:d1 --record-id lifecycle:driver-stopped
    tickets.py set-status <run> <id> stalled

The seals are in each ticket's frontmatter. `B1.10` is already retired; it
only needs the status. Before U2 lands, the second command refuses.

Note that these tickets were sealed by the pre-cleanup trunk, so the
installed trunk will refuse them on the seal. Either settle them from a
checkout of `663ab929`'s `scripts/`, or leave them: the frame is closed and
they block nothing.

## Successors nobody owns yet

None of these blocks anything. They came out of the cleanup run's judges
and its executors, and each names its own evidence.

**Oracles that cannot see what they claim to cover**

- `reader/` sits outside every required check. `reader/tests/test_reader.py`
  lists a module deleted in `338c1678`, and two partitions were red before
  the run and still are. Putting the reader partitions under `run_tests.py`
  or a CI row is the fix.
- No committed check grades a citation into another file's prose. Both
  blocking findings the end judge raised were of exactly that shape, and
  the repair that fixed them has no regression guard.
- `DOCUMENTED_PATH_RE` cannot see a path written inside a backticked
  command, so `` `uv run python scripts/ui.py` `` is invisible to it.
- `sheets/` is the one shipped tree still outside `LINKED_MD_ROOTS`.

**Retired names still in the present tense**

- `reader/web/src` keeps `orch-tdd` and `orch-verify` behind the pinned
  dist, in `WorkflowCatalogView.tsx`, `model.ts`, `data/schema.ts` and
  `catalog.test.tsx`. Fixing it means a dist rebuild.
- `reader/docs/workflows.md` still carries composition prose at `:3`,
  `:29`, `:37`, `:43` and `:53`, backed by that live-but-unfeedable
  frontend branch.
- `scripts/browser_game_validate.py:22` keeps its `BGW-TRACE` run-id
  marker, left alone because the browser-game machinery was out of scope.
- Two run-local ids survive in `installer/packages.py:140` and
  `tools/validate_support/duplication.py:227`.

**Smaller things**

- `docs/vocabulary.md`'s **gate** entry cites `rules/verification.md` §7
  for a sentence that now reads like §6's.
- `scripts/tickets.py:135` binds `_cwd` in `_sync_seams`, which no test
  patches, so that line is a no-op.
- `tests/test_dispatch_standalone.py:145-146` is a vacuous absence
  assertion, and predates this run.
- `tools/run_serial_compat.py` is 519 lines against the 500-line
  presumption. U3's deletions reduce it; nothing splits it.

**Deferred by the cleanup spec itself**

Everything under `example-workflows/`, the shared references bucket, the
browser-game carve-out, and the `research-acquire` ring placement. The
cleanup spec's section 6 is the record of that decision.

## The serial lane, which is a decision and not a defect

U7 closed `limited` on the cleanup spec's own decision 6. It probed
`run_tests.py`'s boundary guard empirically and found it refuses residue on
three of the nine seams the manifest sentinels guard: cwd, import path, and
part of monkeypatch. It restores `environment` without refusing it, and is
blind to event loop, logging, module cache, threads and warnings. So the
serial lane stays, `AGENTS.md` still names five required checks, and the
vocabulary keeps **sentinel**, **shard** and the second sense of **seam**.

Deleting the lane needs that guard widened first. That is a real piece of
work, not a cleanup.
