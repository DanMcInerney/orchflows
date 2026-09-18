# Native workflow dogfood — 17 September 2026

## Result

Across 19 isolated primary trials and one checkpoint continuation, flat composition worked across writing, purchasing, coding, research, video, iterative improvement and custom-workflow authoring. It did not pass every trial. Real execution exposed a child invoking the dynamic fallback and spawning a grandchild, export review happening before its trial, a generated-code defect missed by review, a staged workflow overrunning its test budget, and a game workflow skipping its required core-review gate.

Three small instruction changes address the demonstrated orchestration problems:

1. Dynamic fallback eligibility now explicitly excludes child assignments.
2. Standard review and repair says to wait for the **reviewer to finish**, rather than merely “that review.”
3. Export review explicitly starts **after the trial finishes**.

These clarify existing boundaries and ordering in three Markdown files, adding 12 net words. The malformed-timestamp defect remains in the disposable generated project as failure evidence; it does not justify adding timestamp advice to orchestration instructions.

The corrected Benchmaker rerun stayed flat. The corrected export run performed its trial before authoring review, repaired the export once, and repeated the affected trial. A separate standalone portability run succeeded without Orchflows installed. These are observed successes on one host, not proof that prose can enforce a runtime prohibition in every future run.

## Method and evidence

All work used temporary projects under `C:/Users/danhm/orchflows-dogfood-20260917/`. Each primary trial had a separate Codex home, installed package copies, ordinary request, source fixtures where appropriate, native CLI event stream and content hashes. No normal user library or registration was changed. Model and effort were left unspecified. Test agents did not receive expected answers or the observer's acceptance checks. Trials were launched by this top-level controller; composing trials inside authoring workflows had separate top-level sessions.

The initial task allowance was 15 minutes, with an external process-tree cutoff at 17 minutes. Design Loop hit that cutoff; its pre-continuation workspace and sessions were copied to `design-loop/before-resume/` before a separately recorded six-minute extension. Timings below include setup and are descriptive, not comparative performance measurements: multiple trials ran concurrently.

Evidence:

- `run.py`, `extra_cases.py`, `authoring_cases.py`: requests, fixtures and isolated launch machinery.
- `audit.json`: native session identities, ancestry, settings, assignment calls, completion and artifact paths. Forked parent history is excluded from child-own events. Archived pre-resume sessions are excluded from live counts.
- `output-checks.json`: separately executed output checks, including the explicitly failing malformed-offset case, 604 Evolve compatibility cases and real shopping-list commands.
- `independent-audit.md`: first four outcomes, exact malformed-offset reproduction and original export ordering failure.
- `examples-audit.md`: fan-out, research budgets, numeric evolution and original Benchmaker failure.
- `authoring-media-audit.md`: media and authoring evidence, including trace limitations.
- `inventory.json` and `source-changes.diff`: final run inventory, cleanup, source hashes and this turn's exact changes.
- Each trial's `installed-identities.json`, `request.md`, `events.jsonl`, `exit.json`, `final.md` and native sessions retain the original evidence. Later reruns use distinct directories.

The package version numbers remained those of this uncommitted implementation. Content hashes distinguish the original, ordering-clarified and final fallback-clarified snapshots. Old trials were not silently relabeled as tests of later bytes.

## Dynamic workflow: size and shape

| Ordinary goal | Observed structure | Observed outcome |
| --- | --- | --- |
| Customer maintenance notice, under 100 words | Maker → independent reviewer | Correct 52-word file including its heading; facts preserved. About 99 seconds. Delegating this tiny task was arguably unnecessary overhead. |
| Compare three suppliers with monthly usage and doubled-usage sensitivity | Root makes calculations and recommendation → independent reviewer | All six cost totals independently reproduced; source files unchanged. Birch costs $2,040 normally and $2,560 at doubled usage. About 141 seconds. |
| Build a support-ticket CSV reporting CLI | Maker → whole-result reviewer → root repair and checks | Review found invalid-UTF-8 handling; one repair fixed it. Sixteen separate observer checks passed, but an additional malformed-offset check failed. About 239 seconds. |
| Purchasing pack for six independent branches | Two concurrent makers, three branches each → root gathers and joins → one whole-pack reviewer | All 18 vendor totals, four recommendations, two no-fit branches and $7,976 total checked independently. About 175 seconds. |
| Repeat the same six-branch request after the fallback clarification | One maker while root independently calculates → reviewer | Correct result again. About 251 seconds. Staffing changed without changing the saved workflow. |

This demonstrates adaptive assignment and real fan-out/gather without fixed worker counts. It does not demonstrate optimal staffing. The model spent an extra maker on a tiny notice, then used one maker for a request it previously split across two. Task separability matters more than an arbitrary size tier, and staffing efficiency still depends on model judgment.

### Generated-code failure

The ticket tool accepts an invalid UTC-offset minute value such as `2026-09-02T00:00:00+00:99`. Python's parser normalizes it, while the generated regex accepts any two digits. The tool then replaces existing reports, contrary to the requested invalid-input behavior. The independent reviewer missed this. Both the original successful checks and this failing reproduction are retained; the trial is **not an overall output pass**.

## Example and authoring workflows

| Workflow | Trial and outcome |
| --- | --- |
| Software Factory | Fixed a duration formatter in a disposable Git project. One builder pass and one correctness reviewer; preserved an untracked caller note and produced a reconstructable release handoff. Independent observer checked 10 accepted and 10 rejected inputs. No deployment or remote CI was requested. |
| Social Search | Two concurrent live collectors researched GitHub and Hacker News, each using exactly four acquisition targets. Failed reads counted. Both finished within their deadline, then one assessor ranked the evidence. The root retained the assessor's substantive ranking and preserved coverage gaps. |
| Short Video | Two concurrent makers produced actual editable projects and MP4s: 720×1280 at 8.048 seconds, and 1280×720 at 9.959 seconds. One fresh reviewer inspected both encoded exports and wrote separate findings. Native playback and decoded frames were checked; no ffprobe and no continuous human visual viewing were available. The per-film review wording versus batched reviewer staffing remains a minor interpretation limit. |
| Evolve | Completed two numeric improvement rounds. Review rejected the first, faster candidate because asymmetric custom equality broke compatibility. Evaluation was versioned, the incumbent rechecked, and the second candidate retained the original behavior outside a narrow integer fast path. Numeric review does not establish blind subjective judgment; no subjective-judge claim is made. |
| Design Loop | A two-cycle persistent shopping-list CLI reached a valid accepted first cycle and a second candidate with 10 checks. It exceeded the initial limit during second-cycle review and was stopped. A separately authorized six-minute extension resumed the same run and finished in about 205 seconds, with two attempts total and no restart. Both cycles completed; final integration matched the accepted candidate. Observer add/show/remove, invalid-input preservation and corrupt-file checks passed. The original time-bound failure remains. |
| Benchmaker, original | Built a four-case offline scheduling benchmark, but its no-history audit worker invoked dynamic fallback and spawned a reviewer child. The root detected and interrupted it. The public audit also lacked the README-defined response schema, so correct scheduling choices failed schema grading. Zero target-agent launches were preserved. This run fails flat-orchestration compliance. |
| Benchmaker, corrected rerun | Root authored the package, launched one public-input auditor and a separate final reviewer, waited for both to finish, then repaired once. No grandchildren appeared. Four cases, 16 authored controls, two public audit cases and zero target launches. Its self-test additionally grades a malformed `None` output for case 001, so the strict four-control-outcomes-per-case cap is not established by counting fixtures alone. This validates a synthetic development package's tested machinery, not target calibration or generalization. |
| Export Workflow, original | Reviewed and began repairing before its first representative trial. Later ephemeral-trial summaries claimed independence, but retained execution output is insufficient to verify those nested reviewer launches. This run fails ordering and has an evidence gap. |
| Export Workflow, corrected rerun | Trial before export review. The first ephemeral trial's native reviewer launches failed; separately, that trial then improperly repaired without the required review. Authoring review identified fidelity/process gaps, followed by one export repair and one affected retrial using a persistent session. The retrial and a separate clean standalone run each completed one independent review before one repair. No Orchflows package was installed in the separate portability home; its copied skill text was equivalent with normalized line endings. The successful retry changed both export bytes and host persistence, so it does not isolate which change caused success. |
| Workflow builder | Built a personal `operations-brief` from primitives plus `shared:compare-candidates` and `shared:review-revise-once`. Its fresh top-level trial had four root-owned leaves: options, comparison, draft and review. One repair produced the brief, then a separate authoring review occurred. A run-specific builder review was mistakenly saved inside the library; behavior succeeded, packaging needs that file moved before reuse. |
| Self Improve | A real native run of a deliberately flawed disposable record-count workflow reported four nonempty records instead of two. Self Improve inspected that session and current source, added the existing `--nonempty` flag, fixed input-path handling, ran real fresh trials returning two, and addressed independent-review findings in one pass. This used explicit source-path invocation; registration was not tested. |
| Browser Game | Produced an actual Three.js prototype, editable Blender source and three original GLBs; browser rendering and keyboard input worked. One final reviewer found a dominant straight-line shortcut; one repair added a blocker and verified that exploit no longer won. However, asset production began before the required independent core-review/repair gate, and no separate core reviewer existed. Successful mission completion on either route after repair remains unverified. Runnable output, but **failed full workflow conformance and incomplete final acceptance**. |

Shared comparison and review/repair components were exercised through generated personal and exported workflows. Research Acquire's maintained tests were covered in the earlier test report; this round's Social Search used live native web retrieval and is not a new end-to-end test of every acquisition backend. Software Factory's incident/production-monitoring leaves, model/effort overrides, every genre, every failure path and every host were not exercised.

## What this says about the architecture

The useful stable instructions are role boundaries, dependencies, independent judgment, repair limits and stopping conditions. The root can choose direct work, one maker or several concurrent makers underneath them. Shared workflows were useful: the builder reused comparison and review/repair without inventing a primitive for every activity.

The fallback failure illustrates a boundary that belongs in the workflow: a child must not reinterpret an assigned leaf task as permission to coordinate a new workflow. The timestamp miss and variable staffing are different: task correctness belongs in the project and its checks, while model-specific efficiency advice belongs in guidance when repeated evidence warrants it. Neither calls for a growing catalog of special orchestration stages.

Keep the architecture simple, but distinguish an instruction from enforcement. On this native host children had access to spawning tools, and one violated an explicit assignment before the role clarification. A hard guarantee would additionally require a supported host-level restriction; these trials establish observed behavior, not such enforcement.

The game result is also a reason to revisit that long, method-heavy recipe separately. Its core/final gates were already explicit, so adding more reminders is not a demonstrated remedy. A future simplification should retain those dependencies while moving production techniques into guidance; this testing pass does not silently change that contract.

## Final verification and remaining records

After the source clarifications, the core suite ran **126 tests: 125 passed, one platform skip**. `git diff --check` passed. No permanent test framework, new maintained test suite or new documentation section was added for these temporary trials. The repository changes from this turn are confined to the three existing Markdown files described above; reports and fixtures are outside shipped packages.

All primary controllers and the continuation finished. Every temporary authentication copy was removed. The game left a local server after a command timeout; its command and served source were verified against the generated project before stopping it, and port 4173 was then free. Failed and partial artifacts remain available for inspection.

Independent trace review confirmed corrected Benchmaker's final review finished before package repair, and both persistent export runs finished independent review before repair. The first failed traces remain in the inventory. Remaining concrete issues are the generated timestamp bug, game gate/acceptance failures, strict benchmark control-budget accounting, the builder's misplaced report, and Design Loop's original runtime overrun. These results support the architecture with those qualifications; they do not justify an “all workflows pass” claim.
