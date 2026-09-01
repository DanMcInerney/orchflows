# Architecture successors — 2026-09-01

Work order distilled from run `20260901T181410Z` (the implementation of
[research/architecture-repair-spec-2026-09-01.md](architecture-repair-spec-2026-09-01.md)).
Evidence base: the seam review's findings file, committed in-tree at
`.orchflows/reviews/20260901T181410Z-B1.14-seam-findings.json` (advisory
ids F3-F8 below are its), the run frame's journal (ticket `B1` of that
run in the state sink), and the run's friction entries. Those records
are evidence; this spec is the work order, and its scope is exactly the
items the user picked on 2026-09-01: F3, F4, the three minor advisories
F6/F7/F8, and the run's two process-friction findings. Deliberately NOT
scoped here: the retired-vocabulary lint, and everything on the repair
spec's own Deferred list.

## Standing constraints (every unit)

- The five craft sentences matching `CRAFT_SCOPE_ANCHOR`
  (`scripts/tickets_assignment.py`) stay untouched; word ceilings only
  fall; no T0 shape change — if a unit appears to need one, stop and
  hand back.
- Required checks per AGENTS.md gate every unit; the tip runs
  `python tools/run_required.py --no-cache`. Test changes regenerate
  the serial manifest. Reinstall after merge.
- Acceptance greps that use alternation must pass `-E` (or equivalent):
  this repo's `git grep` defaults to basic regex, where a bare `|` is a
  literal. Run `20260901T181410Z`'s own close-out logged a report whose
  transcribed acceptance command silently matched nothing for exactly
  this reason (run-state note, 2026-09-01).

## S1. Root-walk convergence (F3)

`scripts/_bootstrap.py` owns the repo-root fact but its `ROOT` has zero
consumers tree-wide, while 31 independent `__file__`-relative root
walks survive — one of them in `tools/validate_support/common.py:13`,
the budget-owner module itself. U4's descoping rationale ("tools/*.py
compute their own root to bootstrap sys.path before scripts.* is
importable") is contradicted by `tools/suite_check.py`, which imports
the leaf in the same commit that stated the rationale. Unit: converge
every walk that can lawfully import the leaf onto `_bootstrap.ROOT`;
where a genuine import-order circularity exists, keep the local walk
and document the circularity in one comment at the site. Acceptance: a
repo-wide grep for the walk idiom (`resolve().parents[` and its
variants) finds the owner plus only sites carrying the documented
exception comment; suite green. One child; the F3 finding carries the
site list, but enumerate live sites by grep, not from the list.

## S2. Content-pack commit-clause design pass (F4)

U2 keyed the launch prompt's commit clause on
`adapter_spec(pack).workspace_strategy == "git"`. The `document-tree`
adapter fails that test, so a content-pack child — which works
in-place, without isolation, in a real git tree — now receives no
commit instruction at all. Run `20260901T181410Z`'s B1.1 was exactly
that shape and produced a commit only because the old unconditional
clause told it to. This is a design decision, not a patch: decide what
a document-tree launch says about recording work. The candidate
positions, each with a real cost: (a) document-tree joins the
commit-clause condition (it is a git tree; conflict semantics stay
section-overlap); (b) the content pack's own workspace channel line
carries the recording instruction, owned by the pack craft rather than
the composer; (c) document-tree stops being in-place and cuts
candidates like `git` — which also closes the one-in-tree-worker
serialization constraint the run's wave 1 had to schedule around, at
the cost of changing the adapter's declared meaning. Whatever the
ruling, it lands with launch-composer tests through their owners
(render a content-pack launch and assert the chosen sentence), and the
adapter table's declared cells stay the one source the condition reads.
Acceptance: a rendered document-tree `do` launch states how work is
recorded; the decision and its rejected alternatives are written down
in the unit's report; prompt tests updated through owners; suite green.

## S3. Wrap-insensitive re-pin (F6)

The integrator re-pin at `tests/test_verification_model.py` (commit
645256db) anchors kernel prose including its hard line wrap
("one\nJSON file"). Sound in substance, brittle in form: a reflow of
`skills/kernel/orch-judge/SKILL.md` that changes no words breaks it.
Normalize whitespace before asserting (the file already demonstrates
the pattern — `test_execute_consumes_pack_craft_and_records_post_work_evidence`
joins split text), keeping both anchors. Acceptance: the test passes,
and still passes when the pinned sentence is rewrapped in a scratch
copy; nothing weakened. Trivial; batch with S4 in one child if minted
together.

## S4. Finish the ring's timestamp consolidation (F7)

Two super-research adapters still emit the output timestamp through
their own literal rather than `schema.INSTANT_FORMAT` (the F7 finding
names them; enumerate by grep over
`.orchflows/skills/super-research/`). U12's rule stands: adapters
alias the schema constant; only genuinely distinct upstream
wire-format grammars keep their own. Acceptance: the package grep for
the format literal returns the schema definition plus the two lawful
upstream-grammar constants and nothing else, run with `-E` where
alternation is used; the package's own suite green.

## S5. Give `validate_routing_block` a caller or a recorded berth (F8)

U5(e) shipped `validate_routing_block()` (over
`ROUTING_BLOCK_BUDGET = 400` in `tools/validate_support/common.py`)
with tests but no production caller, because no project-scope
routing-block render surface exists in the tree. Decide once: wire it
into `tools/validate.py`'s pass over the surfaces that do exist today
(`templates/host-block.md`, the rendered managed blocks
`install.py --dry-run` plans), or record at the function itself that it
is the enforcement half of a render surface the host-block split
(repair spec, Deferred) will create, so no dead-code sweep deletes it.
Acceptance: either a deterministic validate failure on an oversized
live surface, or the berth comment plus a pointer from the Deferred
item; no third state.

## S6. The 120-second wall vs the never-background rule (process)

Three of the run's fifteen children violated the launch prompt's "never
background a gate or a test run" line the same way: the host harness
auto-backgrounds any shell command that outlives its default 120s
timeout, scoped suite runs routinely do, and the child then stopped its
turn to wait on a monitor — twice requiring a coordinator nudge to
resume (friction entry 2026-09-01, run `20260901T181410Z`). The
instruction and the harness disagree, and the children lose. Fix where
the fact belongs: the launch prompt's check sentence gains the
mechanism ("with an explicit timeout longer than the check"), or the
pack crafts' verification stage carries it — pick one owner, mind the
prompt's every-line-earns-itself budget (this failure fired three times
in one run; it has earned a clause, not necessarily a line). Update the
launch-prompt test family through its owners. Acceptance: a rendered
launch tells the child how to keep a long check foregrounded; the next
run's children are the live test.

## S7. Workers search the filesystem for what the prompt already hands them (process)

Every `orch-do` launch this run surfaced a long-lived background task
labeled as a search for the skill definition file; B1.1's wrapper
confirmed on cleanup it was a literal unscoped `find /`, fired to
locate the installed skill, superseded seconds later by a targeted
lookup, then left grinding for the rest of the ticket (~62 minutes;
friction entries 2026-09-01, including the correction entry). Two
defects, one investigation: (a) resolution — the launch prompt already
hands the ticket path and the pack craft path, and the installed
`by-name` layout is documented in the host block, which forked
children provably never receive (run `20260901T181410Z` B1.13's
first-person evidence) — so decide the one carrier that tells a worker
where installed items resolve (a clause on an existing launch-prompt
line, or the role agent body at its exact word count) and add it
through owners; (b) hygiene — whatever fires a broad search and then
supersedes it must kill it, which is prompt-side guidance unless
investigation shows the search comes from skill machinery rather than
the model. Verify post-reinstall on a live run: no unscoped filesystem
search in any worker's task list. Acceptance: the carrier decision is
written with its budget accounting; the live-run observation is
reported.

## Execution shape

S1 and S2 are independent one-child units; S2 is the only one needing
a ruling conversation if the executor cannot pick between (a)/(b)/(c)
on the evidence. S3+S4 batch into one small child; S5 is a decision
plus a few lines either way; S6+S7 are one dispatch-surface child
(same composer, same test family, one reinstall check). A judge over
the seams is warranted only if S2 chooses (c) — the others are narrow
enough for the gate plus spot checks.
