# B1.4 — seam review of the self-improve delivery

Run 20260901T132749Z. Merged tip `f1a0d96d01213a40255a4d73d16e1b05fae3049b`
on `claude/self-improve-workflow-design-c2009b`. Read-only review; nothing
in the reviewed tree was edited.

Normative spec: `.orchflows/self-improve-design-2026-09-01.md`.
Artifacts composed: `55d158f3` (B1.1 harvest), `80fda878` (B1.2 events),
`c83e20a5` (B1.3 workflow body + law repoints), `f1a0d96d` (repair).
All four confirmed ancestors of the tip (`git merge-base --is-ancestor`).

## Verdict

Every mechanical check is green at the merged tip and **every defect below
is invisible to all of them.** The five required checks pass (exit 0), both
worker test modules pass (36 and 11 tests, exit 0), and the validator passes
(exit 0). The composition is nonetheless broken in two places where a
shipped surface states something untrue.

Two blockers, three should-fix, three successors.

---

## F1 — BLOCKER — `--list-runs` goal column ships dead (`goal` vs `goal_head`)

**Files.** Writer `scripts/tickets_frame.py:173-175`; reader
`scripts/harvest.py:359-367` (the read is line 366).

    tickets_frame.py:175   "workflow": workflow,
                           "goal_head": (goal_lines[0].strip() if goal_lines else "")[:200],
    harvest.py:366             goals[run] = entry.get("goal")

**Evidence.** Proved end to end against the real CLI in a throwaway sink
(`ORCHFLOWS_STATE_HOME` = temp dir), both commands exit 0:

    frame-open exit: 0
    writer keys: ['event','goal_head','host','project','run','session',
                  'sink_convention','ticket','ts','workflow']
      workflow  = 'self-improve'
      goal_head = 'Harvest the sink and land the top proposal.'
      goal      = None                     <-- what harvest reads
    --list-runs exit: 0
    ROW: ['20260901T999999Z','self-improve','null',
          '2026-09-01T14:47:59Z','2026-09-01T14:47:59Z','0','1']

The goal column is `null` for every run that will ever exist, while the
frame recorded a perfectly good head. Zero exit, no warning.

**Why it is a blocker.** `SKILL.md:17-18` tells the driver `--list-runs`
"prints the candidate runs (id, workflow, goal, counts)". It does not print
the goal. Design lines 94-97 make that column load-bearing: fuzzy resolution
works by it — "the scraper one from a while back" is the line whose goal
mentions the scraper. That resolution path is dead as shipped.

This is exactly the mismatch B1.1's own report predicted it could not rule
out. `--workflow` selection itself survives: that field name matches.

**Fix.** One word at `harvest.py:366` — `"goal"` becomes `"goal_head"` —
plus a test that crosses the seam (see F4).

---

## F2 — BLOCKER — the body tells the mine to copy a digest `watermark` that does not exist

**Files.** `example-workflows/self-improve/SKILL.md:29-30`;
digest shape `scripts/harvest_cluster.py:178-187` and
`scripts/harvest.py:486-502`.

SKILL.md instructs writing proposals

> carrying the digest's cluster_key, matcher and watermark verbatim.

Of those three, the digest emits **one**:

| named in the body | actually emitted |
| --- | --- |
| `cluster_key` | `cluster_key` (harvest_cluster.py:179) |
| `matcher` | `matcher_draft` (harvest_cluster.py:182) — a rename, not verbatim |
| `watermark` | **nothing** |

`grep -n watermark scripts/harvest.py scripts/harvest_cluster.py` returns
only reads of `covered.jsonl` plus the boolean
`window.since_defaulted_from_covered_watermark`. No cluster record and no
digest header carries a watermark. The digest keys are `generated_at`,
`window`, `streams_read`, `totals`, `clusters`.

**Why it is a blocker.** The shipped surface names a field that is not
there, and the failure mode downstream is silent. A covered line written
without a parseable watermark is accepted without complaint —
`tickets.py improvement --covered` appends the caller's line verbatim with
no schema check — and is then **ignored forever** by the exclusion pass:

    harvest.py:318   if ts_dt is None or cov["watermark_dt"] is None or ts_dt > cov["watermark_dt"]:
    harvest.py:319       continue

So the covered-exclusion seam (design Move 1 step 2, the mechanism that
stops the mine re-proposing what was already delivered) degrades to a
no-op with no error anywhere.

**Provenance.** Not B1.3's error. The design contradicts itself: Move 1
(lines 107-109) specifies the digest as `cluster_key`, counts,
`recurrence_met`, `matcher_draft`, members — no watermark — while Move 3's
draft body (line 181) tells the mine to copy one. B1.3 shipped the draft
faithfully and inherited the contradiction.

**Fix.** Either emit a watermark in the digest (the harvest's window end,
or `generated_at`) or reword the body to name `generated_at` and
`matcher_draft` by their real spellings. Prefer emitting it: the covered
line's watermark should be the harvest's window end, which only the harvest
knows.

---

## F3 — SHOULD-FIX — `--workflow` has no producer anywhere in the tree

`--workflow NAME` on `frame-open` is optional
(`scripts/tickets_frame.py:128`), and `_run_workflow_map` skips any
frame-open whose `workflow` is null (`harvest.py:253`). **No workflow body
in the repository passes it** — including self-improve's own:

    example-workflows/self-improve/SKILL.md:34
        tickets.py frame-open <run> --goal-file <frame-goal>

Grepping `--workflow` across `example-workflows/` matches only the harvest
usage block at SKILL.md:14. The other eight workflow bodies
(benchmaker, browser-game, drift-canary, evolve, renovate,
skill-tournament, super-research) all call bare `frame-open` too.

The design calls this the event stream's headline justification — Move 2,
line 119: "workflow name (this is what makes `--workflow` a selector: one
workflow's every run, across all time, is a slice)". As shipped, every run
records a null workflow, so `--workflow` matches nothing.

**Compounding with F1 this is severe:** for every run the shipped bodies
actually open, `--list-runs` prints run id, timestamps and counts with
`null` in *both* the workflow and goal columns. The resolver mode — the
entire reason `--list-runs` exists — returns no distinguishing information
at all. F1 and F3 should be fixed together.

**Fix.** `--workflow self-improve` on SKILL.md:34 is in this delivery's
scope. The other eight bodies are a successor.

---

## F4 — SHOULD-FIX — the vacuous green: no test crosses the writer/reader seam

Both halves are tested; the seam between them is not. This is why F1
shipped green.

- `tests/test_events.py:139-147` asserts the writer's `goal_head`. Correct.
- `tests/test_harvest.py:406-413` — `test_run_with_frame_open_reports_workflow_and_goal`
  — asserts `["R1","self-improve","Deliver the thing"]`, green only because
  its own fixture builder invents the reader's spelling:

      tests/test_harvest.py:61-66
      def _frame_open(ts, run, workflow, goal):
          return { ... "event": "frame-open", "workflow": workflow, "goal": goal }

  Against the real writer that assertion reads `["R1","self-improve","null"]`.
- Grepping `harvest` in `tests/test_events.py` returns no matches. Nothing
  composes the two halves.

The test names the goal column and would **not** fail if the writer's field
name changed, because the writer is never involved. That is the precise
answer to the vacuous-green question: B1.1's list-runs test does not anchor
the behavior it claims to.

**Corroboration that the fixture was invented rather than derived from a
real line:** it hardcodes a string `sink_convention` of
`"orchflows.events.v1"` while the real writer emits `SINK_CONVENTION = 2`,
an integer (`scripts/tickets_store.py:30`). Harmless — harvest never reads
that field — but it proves no test ever saw an event line the trunk
actually wrote.

**Fix.** One test that calls the real `frame-open` and then the real
`--list-runs`, asserting the goal column. The proof in F1 is that test.

**The other half of the question — did the repair's reword detach an anchor
B1.3's validator pass relied on? No.** `tools/validate.py` exits 0 at the
tip; its warnings are all pre-existing near-duplicate notices on unrelated
files (contracts/, rules/topology.md, skills/kernel/), none on any file
this delivery touched.

---

## F5 — SHOULD-FIX — the inline-mine path reaches Deliver with no frame to name

The body binds `frame-open` to the mine-brick branch only:

    SKILL.md:31-36   Larger, or when independent eyes are wanted, spend one
                     brick, which opens the frame:
                         tickets.py frame-open <run> --goal-file <frame-goal>
                         tickets.py do <run> ... --parent <frame> ...

but both later steps require a frame unconditionally:

    SKILL.md:45-46   tickets.py do <run> --pack orch-code-pack --parent <frame>
    SKILL.md:68      Return: tickets.py frame-close <run> <frame> --done <gate>

On the design's *cheapest and most expected* path — a digest at or under 40
entries, mined inline, then delivered — no frame was ever opened, so
`--parent <frame>` and `frame-close <frame>` have nothing to name. This is
the repair child's flagged deviation, and it is real.

The design did not have this hole: line 186 reads "the frame opens with the
first brick", which generalizes over *whichever* brick comes first. B1.3's
edit narrowed that to the mine brick specifically. Not a blocker — it fails
loudly, a driver cannot fill in the frame id — but it is a live authoring
defect on the common path.

The `Return:` paragraph B1.3 added (absent from the design draft) is
otherwise correct and matches house convention; it only inherits this
problem, and also restates "Close with `frame-close`" already in the frame
law paragraph.

---

## Successors

**S1 — `rules/improvement.md:48` overstates after the repoint.** Section 6
still ends "one run in the sink per cycle", but the new body has two paths
that open no run at all: the empty digest ("no frame, no ticket",
SKILL.md:23-24) and inline mining. Section 6 as re-pointed does not
contradict sections 4-5, the body's delivery obligations, or
`rules/visibility.md:44-48` — the qualify-step removal and the harvest
sentence are all consistent — but this tail sentence now asserts more than
the workflow does.

**S2 — events carry no `skill`, so `--skill` zeroes the event column.**
`_matches_selectors` (harvest.py:196) tests the entry's `skill`, which is
always absent on events; `tickets_result.py`'s `_event_host` docstring
declares the omission deliberate. Consequence: `--list-runs --skill X`
reports zero events for every run. Correct-by-construction, worth a line in
the docstring so a future reader does not read it as a bug.

**S3 — file sizes past the 500-line presumption.** `scripts/harvest.py` 537
and `scripts/tickets_frame.py` 571 (warn-only presumption, not a cap).
Neither is a real violation: harvest.py carries a 64-line module docstring
(~473 lines of code) and already grew sideways into
`scripts/harvest_cluster.py` (197), which is exactly the craft's remedy;
tickets_frame.py was already over 500 before this delivery and grew 22
lines. Recorded, not charged against this work.

**Nit, not a finding.** `rules/visibility.md:45-47` says events are
"written only by `scripts/tickets_frame.py` and `scripts/tickets_land.py`".
The append is actually performed by `tickets_result._append_event`, which
those two call. Accurate at the transition level and followable in one hop.

---

## What was checked and found clean

- **Provenance head, field by field.** Writer emits `sink_convention`,
  `ts`, `project`, `run`, `ticket`, `host`, `session`, `event`. Reader's
  selectors match on `session`, `run`, project `name`, and `host`. Verified
  `_event_project` returns a dict carrying `name` (root, origin, name =
  orchflows-public), so `--project` works on events.
- **Timestamp format.** Writer uses `UTC_STAMP` of `%Y-%m-%dT%H:%M:%SZ`
  (`tickets_store.py:29`); the reader's `_parse_timestamp` parses that exact
  format. Match — this is what B1.2's repair commit `80fda878` fixed.
- **Host strings.** `tickets_result._event_host` returns
  `claude-code`/`codex`/`unknown`, byte-identical to
  `friction.py:_detect_host` (lines 331-337), so `--host` slices both
  streams alike.
- **Event kind names.** Writer emits `frame-open`, `frame-close`, `land`,
  `stalled`; the reader's `FRAME_OPEN_EVENT` constant is `frame-open`.
  Match.
- **`_run_workflow_map` is built from all events unfiltered**
  (harvest.py:468, before window resolution) — correct, and its docstring
  says why: a run's frame-open can fall outside the window its later
  friction lands in.
- **Prose/CLI seam.** Every command and flag SKILL.md names exists with
  that spelling: `--list-runs`, `--out`, `--since`, `--until`, `--on`,
  `--session`, `--run`, `--project`, `--workflow`, `--skill`
  (`harvest.py:397-410`); `frame-open`, `do`, `judge`
  (`tickets_commands.py:49`), `improvement --proposal` and `--covered`
  (`tickets_result.py:46`). Only the two *field* names in F1 and F2 are
  wrong, never a command.
- **Move 3 semantics survived the repair reword.** The seam-judge close
  rule, the single-child unjudged sentence, and all five Never items carry
  the design's meaning word for word. The frame-law paragraph compressed
  "relay `artifact:` and `findings:` lines verbatim" to "keep `artifact:`
  or `findings:` word for word" — an and/or swap, no loss in context.
- **Word budget.** SKILL.md body 450 words against the 450-word workflow
  tier budget; `tools/validate.py` exits 0.
- **Installer.** `harvest.py` registered in both `SCRIPT_NAMES` and
  `SCRIPT_SUPPORT_PREFIXES` (`installer/inventory.py`), so
  `harvest_cluster.py` ships too. `install.py --dry-run` plans 317 entries,
  exit 0.
- **Derived-artifact join.** `tests/serial_compat_manifest.json` was
  regenerated independently on two branches (`55d158f3` and `80fda878`)
  and merged; `tools/run_serial_compat.py` exits 0 at the tip, so the
  merge resolved correctly.

## Commands run, exit codes as observed

| command | exit |
| --- | --- |
| `git merge-base --is-ancestor` on each of the 4 artifacts | 0 (all ancestors) |
| seam proof: real `frame-open` then real `harvest.py --list-runs` | 0 / 0 |
| `tools/validate.py` | 0 |
| `python -m unittest tests.test_harvest` | 0 (36 tests) |
| `python -m unittest tests.test_events` | 0 (11 tests) |
| `tools/run_required.py --no-cache` | 0 (all five: validate, run_tests, run_serial_compat, install dry-run, git diff check; tree 8e27c1ea6029) |

## Deliberately not done

- **Did not edit anything.** Goal fixes this review as read-only; every
  finding above is reported, none repaired. Per the pack's Lens, contract
  and shape findings are reported and never repaired in the same run.
- **Did not re-run the per-child oracles as child oracles.** Goal forbids
  it. `test_harvest` and `test_events` were run for one purpose only —
  answering Goal item 4, whether those greens still anchor real behavior at
  the merged tip — which cannot be answered without observing them.
- **Ran the full required five deliberately, despite the unit rule.** This
  ticket carries `independence: gate`, and two children regenerated the
  same derived artifact (`serial_compat_manifest.json`) on separate
  branches. Only the join can see whether that merged correctly. It did.
