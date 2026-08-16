# Library review — 2026-08-16, pass 2 (skills, compositions, documentation, fallbacks)

Second pass of the day, on the tree the first pass and its follow-ups
left (PR #58, `main` = dc11400 = 3615116). Asked for: every skill's
wording and structure as terse, flexible and well constructed as the
law allows; the compositions' structure and design; documentation
current; no fallback code or methods; the whole library for
consistency, simplicity, speed and quality — and, first, an adversarial
review of the previous handoff. Run `20260816T191118Z-adhoc-skills-review`
in the state sink: eight blind read-only `orch-critique` lanes (H the
handoff; S1 kernel+engines; S2 workflows+utilities; S3 instances+packs;
S4 compositions; S5 super-research; D documentation; F fallbacks), one
`orch-synthesize` join over their packets, then thirteen repair tickets
(R1–R5, R6a/b, R7, R8, R9a/b, R10, C-1, C-2, C-3) each run as executor → §10
checker → fresh re-verifier → `orch-integrate` → `--no-ff` merge, in
host worktrees. Every lane's ticket, checker pass and verdict is in the
sink; this file records what landed.

## 0. Header

- **Commit** 3615116 → this change set, branch `claude/skills-review-2026-08-16`.
- **Law text** (rules + contracts + skill bodies; whitespace tokens,
  link targets and frontmatter stripped): 1,314 non-empty lines /
  10,709 words → **1,277 lines / 10,339 words** (−370). Skill bodies
  4,067 → 3,669 (−10%); their references 1,935 → 1,743; packs 2,711 →
  2,613; compositions 10,722 → **9,305** (−13%); root documents
  (README, ARCHITECTURE, DESIGN, AGENTS) 6,055 → 5,604; super-research
  8,851 → 7,840; every shipped `.md` outside tests and benchmarks
  54,405 → 50,792 (−3,613, −6.6%). Executor-child load for one
  `orch-tdd` dispatch, by the R-2 method: 2,590 → 887 words.
- **Validator** exit 0, 0 ERROR, 8 WARN (the same eight near-duplicate
  pairs as at 3615116); **tests** 1,903 → 2,004 (+101, every one a red-first pin of a behaviour a lane changed), 0 failures
  under the sharded runner and the serial discover; `install.py
  --dry-run` 229 → 228 (self-improve/02-close no longer shipped); `git
  diff --check` clean; preflight ok on 3.9 / 3.11 / 3.12 (the interpreters installed here; 3.13 and non-Windows stay CI's) — its first run was red on 3.9 alone, closed by C-2.
- **Friction** this run: 9 entries; 62 synthesized threads from 72
  lane findings, 75 coverage rows, nothing dropped.

## 1. Verdict

The first pass had cut copies at the seams; this pass found the
**producers still missing behind the law** and the **fallbacks the
scripts kept where the prose says there are none**. The three moves
that closed most threads: (1) the §10 checker path got its producers —
`tickets.py check`, `packet --executor orch-critique|orch-verify`, a
packet that carries the close law — so four instance bodies stopped
sending every executor to a 1,690-word contract; (2) every script path
that turned a failure into "nothing there" now names itself
(friction.py, cutcheck, tickets.py `ready`, ui.py, validate.py,
install.py's receipt, migrate_state, preflight, the visualize
verifier/renderer, super-research's runner); (3) the compositions were
read as data — evolve's done state, the tournament's evaluation,
benchmaker's unowned stages, seven manifests' boilerplate, a stub that
re-verified its predecessor's gate — and cut to what each stub reads
and returns.

## 2. Threads landed (ticket · owner · change)

1. **R1** `scripts/tickets.py`, orch-critique/verify/integrate —
   `check <run> <id> --by` writes `checked_by`; `packet --executor`
   emits the further child's packet (profile resolved from that skill);
   the executor packet carries the close law; `ready` returns `skipped`
   for what it could not read; lease helpers return their failure arms;
   `run-state` refuses on unreadable notes; the checker's law said once
   (critique 203 → 171 body words, verify 195 → 175).
2. **R2** kernel/engine bodies — frontier 442 → 396 (checker line names
   the `--executor` packet, re-verify scoped to what the checker
   invalidated), profiles.md 548 → 454 (copies gone; the watch names the
   successor a worktree session may use, never a wait loop), loop
   195 → 138 (claims its iteration), decompose 293 → 229,
   investigate 142 → 109. Declined with evidence: the
   dependency-ordered-overlap sentence (pinned as decompose's owned
   rule); the loop→frontier merge (not the smallest fix).
3. **R3** instances/packs/cut-lens — no instance body links
   work-item.md; tdd/render no longer restate the workspace command;
   twelve pack-reference framing lines gone; the git packs' deviation
   cites the record that exists; draft names the stamped pack's craft;
   resolve-conflicts returns a revision; cut-lens 386 → 280 (epilog
   copy gone; the move of its git method declined on the recorded owner
   decision).
4. **R4** workflow bodies — eval-design's record is its Return; spec
   loses its unreturnable exit, its contradictory successor rule and
   two copies; repair binds the defect set whichever producer supplies
   it; self-improve names bare scripts; build and triage stop
   restating (net −118 words; the "untrusted" clause kept by ruling).
5. **R5** orch-visualize — verifier exits 2 without the CLI (structural
   fallback deleted, 167 lines); renderer's cdn mode deleted; geometry
   it cannot read is a warning; authoring.md claims only what the lint
   does; body 226 → 190.
6. **R6a/R6b** compositions — evolve's done state stated once; the
   tournament hands evolve a promotion rule and margin; benchmaker's
   evidence-store root, manifest writer and triage pass owned; its inert
   `bound` placeholder gone; the self-qualification guard once; protocol
   copies cut; `self-improve/02-close` deleted; drift-canary
   instantiates; renovate stops forbidding what its packet refuses;
   `contracts/work-item.md` owns the template bound (+11 words) and
   seven manifests lost their boilerplate; seven copied `profile:` lines
   gone; per-unit pack-stamping clauses deleted (D-4).
7. **R7** super-research — a read nobody answered is a typed
   `unreachable` step that bills no call and keeps prior records;
   protocol.md 5,135 → 3,161 with the maintainer half in internals.md;
   body 334 → 227 with the parse hop and a channel-form Return; the
   mirror stub carries no absolute path; 171 `findings.md` citations
   retitled.
8. **R8** documentation — README states routing once and claims only
   what trace.py does (1,850 → 1,654); ARCHITECTURE's installer prose is
   one pointer (913 → 735); DESIGN's dead names and stale facts;
   library-review names where a report lives; vocabulary drops an
   unconsumed term; no shipped doc links DESIGN.md.
9. **R9a/R9b** installer and run-state scripts — the receipt names its
   source commit from a worktree and tells a corrupt receipt from none;
   the rendered role agents send no child to read roles.md (body 51 →
   41 words); friction.py refuses a malformed argv and names an internal
   failure; ui.py renders a read failure as `DIAGNOSTIC_UNREADABLE`;
   validate.py warns per skipped check; state_root, doclint, isolate,
   trace resolvers name themselves.
10. **R10** cutcheck names what it could not read (`UNREAD`, a failed
    HEAD clone exits like a failed baseline clone); preflight refuses an
    unreadable matrix and names the OS from `sys.platform`;
    migrate_state refuses an unreadable destination.
11. **C-1** post-merge — the ten cross-ticket residues (improvement.md's
    stage list, loop's exit citations, work-item.md's `checked_by`
    producer and hollow reply_to pointer, the frontier reading `skipped`,
    a dead `LICENSED_COPIES` entry, a stale docstring, the same-date
    report suffix, verification §10 vs the frontier's re-verify clause,
    loops.md's nested-stall contradiction, the unused `roles_path`) and
    the one seam no lane could see: R6a retargeted a guard at a clause
    R4 trimmed — each green alone, red merged.

## 3. Declined or queued (with reason)

- cut-lens.md:27-41 → code pack oracles.md: `tests/test_carriage.py`
  records the owner decision; no new evidence.
- orch-loop as a one-ticket frontier run: `rules/loops.md` §9 offers the
  frontier as one of three caller-supplied forms; the claim gap closed
  instead.
- benchmaker manifest `measurement` component (T28b): a live key in
  `benchmarks/benchmaker/manifest.json` and the fixture — candidate scope.
- three ui.py sites need a route-layer channel, not a marker; a
  vega-lite dependency line for the renderer (an `add`).
- reply_to's non-inference reason is stated nowhere tree-wide (already
  so at 3615116); `rules/token-economy.md:68-71`'s dated event in a law
  file (lane D's deletion 2) — the user's call on a rule.

## 4. Decisions for the user (evidence in the run's tickets)

- **Delete `REVIEW-2026-08-06.md`** with `tests/test_validate.py`'s
  entry: cited by nothing but its successors' headers; the report-home
  clause now says a report is deleted once its successor records what
  landed.
- **evolve's kept-incumbent path never reaches `03-result`**: it closes
  `limited`, a non-complete terminal, and the frontier blocks
  dependents of any non-complete terminal — a second legitimate done
  check (generation count exhausted) or the frontier releasing
  dependents on `limited`.
- **Seven planner→worker `profile:` overrides** on stubs (renovate,
  benchmaker/04-audit, four decompose stubs): a cost decision to record
  once, or delete.
- **`.orch/canary` items name `executor: orch-trivial`**, which no skill
  provides, so drift-canary still cannot drain end to end.
- **Delete `fix/03-verify`** (one child fewer per fix run) now that the
  checker path has producers; `tests/test_tickets_view.py` pins four stubs.
- **The closure resolving `<skill>'s Return`** so stub Returns shrink to
  "per <executor>'s Return" — the single simplifying move no lane owned.
- **Per-unit pack stamping**: both clauses instructing it were deleted as
  unbacked; a multi-domain case set now needs one run per pack unless
  orch-decompose is amended.
- `~/.claude/agents/orch-planner.md` is user-customized and kept by the
  installer: re-apply the roles.md cut by hand or delete and reinstall.

## 5. Five safest further deletions (each with its ablation)

1. `templates/host-block.md` / `README.md:44-52` overlap on the three
   routing branches — ablation: one cold routing session per branch.
2. `rules/token-economy.md:68-71` (the dated fall) — ablation: grep
   "460": REVIEW-2026-08-16.md:184 and tests/test_installer.py record it.
3. `DESIGN.md` §"Why session tracing is post-hoc" — ablation:
   `schema_confidence`/`parse_errors` are trace.py's docstring's.
4. `.orchflows/skills/super-research/references/protocol.md` "What the
   evidence says" — ablation: evidence.md holds every fact; the
   loss-table test keys on its own headings.
5. `install.py` `_uninstall_boundary`'s `except … continue` /
   `return Path.home()` — unreachable after `_auto_remove_path_is_safe`;
   ablation: the uninstall tests with the return replaced by `raise`.

## 6. Meta

Two connecting causes. **Prose that named a producer no script had**
(`checked_by`, `workspace.py check`, the close law, the report's home)
— every lane found one, and each cost a hand-written packet or a
silently unmet contract until R1 built the verbs. **A None or exit 0
doing double duty for "absent" and "failed"** — friction.py, cutcheck,
tickets.py, ui.py, validate.py, install.py, migrate_state, preflight,
the visualize scripts: the same shape twelve times, each defended
locally as a stated default. The one thing this pass could not do from
inside a lane: thirteen worktrees each green alone were red merged on
one pin — the join must re-run the suite on the integrated tip after a
merge batch, and nothing in the tree yet grades a merge the way a lane
grades itself. That is the next producer gap.

## 7. The handoff (lane H)

`HANDOFF-remaining-work.md` was reviewed as a fixed artifact: nine
findings — its resume test leaned on a receipt field that is null from
a worktree install (fixed by R9a); item 1 had already run; item 6's
doclint count and location were false (1,222 near-duplicates, 83
outside benchmaker cases, 4 in library prose no exclusion clears); item
3 misattributed all three evidence claims; item 2's diagnoses missed
that instance bodies linked work-item.md twice and that the agent-file
fold arm was 105 words over an 80 ceiling; omissions (profiles.md's
wait loop against the host block; three dangling links in the
installed library; the receipt). Items 1, 2a, 2b, 3 and most of 4–10's
neighbourhood landed here (R9a, R3, R8, R10); the rest is in this run's
handoff in the sink, which supersedes it.
