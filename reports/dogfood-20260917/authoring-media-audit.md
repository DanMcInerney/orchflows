# Independent audit: authoring and media trials

Read-only inspection of completed `short-video`, original `export-workflow`, `self-improve`, `builder`, and `export-recheck` runs under `C:/Users/danhm/orchflows-dogfood-20260917`. Evidence includes installed workflow instructions, native session metadata/tool calls, nested CLI output, artifacts and independently recomputed hashes. Original trial files were not edited. The separately queued clean-host `export-portability` trial is not included.

## Results at a glance

| Run | Supported conclusion | Qualification |
| --- | --- | --- |
| Short Video | Two concurrent makers produced real MP4s; an independent reviewer inspected the encoded outputs and wrote separate reviews. | Both films were batched into one reviewer assignment; continuous motion was played programmatically, with sampled visual inspection. |
| Self Improve | Historical command defect identified, minimally fixed, trialed, independently reviewed, repaired once and trialed again. | Explicit-path invocation; ephemeral review wrapper timed out after the full verdict was emitted. |
| Builder | A generated personal workflow actually composed primitives and shared components in a separate persistent top-level trial with four flat children. | Final doc cleanup was not behaviorally rerun; one actual review record was misplaced inside the installable library. |
| Original Export | Corrected memo and portable-looking skill files exist. | Authoring review ran before trial evidence; nested independent-review claims are not fully auditable from truncated output. |
| Export Recheck | Authoring trial preceded export review; a later persistent trial demonstrably completed independent review and one repair. | Initial ephemeral launch failure and subsequent unauthorized process fallback remain real failures; the later pass does not erase them or prove clean-host portability. |

## Short Video: actual media, bounded inspection

The root dispatched `make_humor` at 00:14:00 UTC and `make_personal` at 00:14:12. They completed at 00:16:45 and 00:16:37 respectively. Each wrote only its own film's project/export/check area. The root gathered their outcomes, then dispatched `review_films` at 00:17:17. No child launched or assigned another agent, and neither source nor export was repaired after review.

These are actual encoded exports, not project-only success claims. The reviewer used local Chrome/Playwright to decode each exact MP4, seek and save frames, play the entire file at normal speed to `ended`, and inspect frame images through `view_image`. Its tool trace includes both playback-script outcomes and image inspection calls. It produced separate per-film findings, including the personal film's layered crossfade at approximately 8.35 seconds.

I viewed two decoded review frames and independently recomputed the export hashes:

- `short-video/workspace/humor/export/fridge-again.mp4`: 1,199,244 bytes; SHA-256 `0df0d867461f0c333409f64fe39cd2da33e96d4bb0664f80763bee25f446e309`; recorded decode 720×1280, 8.048133 seconds.
- `short-video/workspace/personal/export/corner-brownie-thank-you.mp4`: 948,556 bytes; SHA-256 `7edee7e851296be58ee4574ed75b68b2f60e0cfb402edfa7789c6843e190d001`; recorded decode 1280×720, 9.958833 seconds.

The reviewed frames support drawn-shape/text production and the supplied joke/memory. I did not independently watch every frame. Browser playback does not establish perceptual inspection of continuous motion; string markers such as `vide`/absence of `soun` are weaker than full container-stream enumeration. The final handoff appropriately discloses those limits, missing ffmpeg/ffprobe and a 30 fps capture target rather than claiming independently measured constant frame rate. Durations are approximate to the requested lengths, not exactly 8.000/10.000 seconds.

Staffing nuance: the wrapper says to invoke review-short-video once per film, while this run used one fresh reviewer for both films. Both were independently reviewed and received separate reports, but this is not evidence of two separate primitive review invocations. Because the wrapper also assigns staffing to the orchestrator and requires no independence *between films*, this is a minor ambiguity between literal invocation count and flexible batching, not a demonstrated loss of review independence.

Evidence: root `short-video/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-11-53-01a0b1da-f934-71e1-b041-2661f4478324.jsonl`; reviewer `rollout-2026-09-17T20-17-17-01a0b1df-ed7d-7161-9781-34e2a89c91aa.jsonl`; each film's `review/inspection.json` and `review/review.md`.

## Self Improve: a real fix with recoverable timeout evidence

The root inspected the supplied native history using the history CLI and checked current personal-library source. The workflow promised nonempty records but omitted the script's existing `--nonempty` flag. It added that argument, retained the script, and ran a fresh top-level CLI trial. Actual captured trial output includes reading the skill, executing the corrected command and writing result `2`; this is stronger than the final message alone.

After that trial, a separate fresh CLI review examined the stable skill, regression materials and trial evidence with explicit no-edit/no-delegation instructions. The command wrapper eventually returned timeout **124**, but the captured output already contains the complete final four findings and verdict, and `independent-review.md` was saved at 00:20:12. The root began repairs at 00:20:43. Therefore the timeout is a wrapper/process-completion anomaly, not evidence that no review occurred or that repair preceded receipt of its final findings.

One coordinated repair added absolute input-path resolution, a self-contained regression fixture and stronger evidence. A second fresh trial at 00:21:06 successfully resolved relative `input.txt`, ran the script with `--nonempty`, and wrote `2`. Before/after hashes match in the raw command results; independently recomputed current hashes match the recorded input, script and skill identities. No second review was falsely claimed. The historical workspace was used read-only in the inspected commands.

Limits remain as disclosed: the personal candidate was addressed by source path, not installed name; missing/unreadable files, all-empty input and paths with spaces were not tried. Adding a correct flag and clarifying a path is a narrow workflow correction; no new orchestration layer was introduced.

Evidence: `self-improve/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-14-51-01a0b1dd-b324-7d10-a953-1bceffee0e61.jsonl`, especially nested outputs at lines 82, 135 and 155 and repair at line 140; workspace `trial-evidence.md`, `independent-review.md`, and `personal/skills/count-records/SKILL.md`.

## Builder: substantive composition succeeds

The author created a reusable `operations-brief` library with invocation-specific questions/sources/criteria supplied at runtime and writing preferences in personal guidance. Its completed persistent top-level trial used this sequence:

`options_work → shared comparison → brief_draft → shared review/revise → root repair and verification`

Native records prove four fresh children under the trial root: `options_work`, `options_compare`, `brief_draft`, `brief_review`. Each dependent stage started after its prerequisite completed. The draft reviewer returned two concrete findings at 00:21:09; the root repaired at 00:21:40 and preserved distinct original/delivered files. No child delegated. This is direct evidence that a user's custom library can compose shared workflows while the root owns all dispatch.

The resulting brief accurately distinguishes estimated setup and unmeasured savings from facts, excludes the hosted option under current authorization, and recommends a conditional internal pilot rather than carrying it out. The native comparer and draft reviewer files support those judgments. Independently recomputed original/delivered hashes match the trial record.

Only after the trial completed did the author launch its own independent workflow reviewer. It then removed duplicated component/guidance prose, qualified host invocation-policy claims and added existing native session identifiers to evidence. These final changes did not introduce a new functional stage; the absence of another trial is not clearly a violation of the rule to repeat *affected* behavior. Exact final wording nevertheless lacks a fresh execution of its own.

One concrete packaging defect remains: `builder/workspace/personal/trials/ordinary/builder-review.md` stores this run's actual review findings/disposition inside the personal library. Core architecture assigns run outputs to the caller workspace, while reusable trial requests/expectations belong in the library. Move such a record outside the package in a real implementation; the frozen test artifact was left untouched.

Evidence: trial root `builder/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-16-12-01a0b1de-f06a-7da1-8a60-c2bc73beac94.jsonl`, its four child traces, authoring root `rollout-2026-09-17T20-14-15-01a0b1dd-26b2-7173-9668-640b76559994.jsonl`, and `builder/workspace/trial-workspace/outputs/`.

## Original Export: correct artifact does not establish process compliance

The previously recorded ordering failure remains: authoring review launched at 00:13:48 before representative trials; repair began at 00:15:04 before that reviewer finished at 00:15:14; the first trial launched at 00:15:45. That review could not assess later trial evidence. Finishing trials afterward does not retroactively satisfy the intended order.

The two nested trials used `--ephemeral --ignore-user-config`. Their retained CLI outputs at root lines 107 and 148 are truncated across the execution middle. There is no persisted child tree or separate untruncated trial stdout file. Generated evidence reports state that a fresh reviewer acted, but those assertions alone do not prove a native independent review. This is **inconclusive**, not a demonstrated successful delegation or a proven fabrication.

The first memo corrected explicit contradictions but omitted dashboard impact and the status URL. The author then strengthened the representative request to explicitly require every supplied fact and reran with corrected path preparation. The second memo contains all supplied facts, and its preserved original hash matches. This is a documented change to the trial prompt/preparation; it does not establish an unchanged-request improvement in exported workflow behavior.

The final “passed independent review” claim therefore exceeds the retained auditable execution evidence. Source portability also was not isolated from all installed Orchflows availability in these runs.

## Export Recheck: corrected order, host failure and valid persistent retry

The recheck visibly trialed the export before launching authoring review at 00:21:13. That exercises the clarified phase ordering on this request; it does not prove all callers will comply.

Its first ephemeral trial attempted two reviewer launches. Native stderr captured in the parent trace records `collab spawn failed: no thread with id` at 00:20:02 and 00:20:09. That is an observed host/service failure. Separately, the trial root then chose to repair the memo despite lacking the required independent assessment. It disclosed the missing review, but disclosure does not satisfy the review-before-repair dependency. Treat the launch failure and this model decision as separate findings.

After authoring review and one export repair pass, a persistent fresh trial started at 00:23:25. Its native root launched `independent_reviewer` at 00:23:58; the child completed at 00:24:25 without edits or delegation; root repair followed at 00:24:32. Original preservation and all supplied facts are supported by tool evidence. This is a genuine successful review/repair path, unlike a report-only assertion.

The successful retry changed both host persistence and export bytes. It supports this specific repaired export on a persistent host; it does not isolate which change caused success, erase the first failed process, or prove operation with Orchflows absent. The separate clean-host portability trial is needed for that narrower claim and was not audited here.

Evidence: `export-recheck/workspace/trial/evidence/trial-events.jsonl`, parent trace `export-recheck/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-17-20-01a0b1df-f744-7150-93f6-adc2553e4bf4.jsonl` line 109 for host errors, persistent trial `rollout-2026-09-17T20-23-25-01a0b1e5-8a14-7132-8215-891bb308782f.jsonl`, and reviewer `rollout-2026-09-17T20-23-58-01a0b1e6-0c13-7632-acb0-21d52dac4b46.jsonl`.

## Supplemental completed-run audit

Added after the clean-host portability and browser-game trials completed. Times below are UTC on 18 September 2026. Native trace paths are relative to `C:/Users/danhm/orchflows-dogfood-20260917/`; session files are under each trial's `codex-home/sessions/2026/09/17/`. Child-own tool events were distinguished from forked parent history at the child's assignment boundary.

### Corrected review and repair timing

| Run | Required judgment finished | Next consequential action | Result |
| --- | --- | --- | --- |
| Benchmaker recheck public-input audit | 00:24:12.852 | Separate final reviewer launched 00:24:30.046 | Public findings gathered before final package judgment. |
| Benchmaker recheck final review | 00:25:38.558 | Package repair tool 00:26:11.396 | Actual repair followed both judgments. |
| Export recheck initial top-level trial | Completed tool output received 00:21:04.297 | Export reviewer launched 00:21:13.161 | Representative trial preceded export review. The trial's own missing-review failure remains a failure. |
| Export recheck authoring review | 00:22:49.376 | Export repair tool 00:23:03.430 | Actual patch followed reviewer completion. Root announced applying repairs at 00:22:47.460, about two seconds early, after an interim reviewer message. Do not describe that announcement as proof of final gathering. |
| Export recheck persistent retrial review | 00:24:25.519 | Memo repair tool 00:24:32.556 | Correct independent-review-before-repair ordering. |
| Standalone export portability review | 00:27:23.319 | Memo repair tool 00:27:29.783 | Correct independent-review-before-repair ordering. |

Benchmaker recheck root trace is `rollout-2026-09-17T20-19-51-01a0b1e2-462d-7cb3-b2e2-b8ba30dedb94.jsonl`: public audit spawn line 56, final review spawn line 73, first package repair line 91. Its two child traces end at lines 35 and 40 respectively: `rollout-2026-09-17T20-23-35-01a0b1e5-b2ca-7192-8bce-406d0207c1f0.jsonl` and `rollout-2026-09-17T20-24-30-01a0b1e6-8671-7563-b197-9d33403a2d9f.jsonl`.

Only those two depth-one children appeared. Neither delegated, continued another child, nor launched a CLI agent. The public auditor initially considered the dynamic fallback, read its skill at 00:23:41.589, then explicitly recognized the new child exclusion at 00:23:45.093 and proceeded directly. Its own reads were the two designated inputs, selected public README sections, and benchmarking guidance; no evaluator material was read. This supports the specific fallback correction more strongly than mere absence of a grandchild would.

Budget qualification: `benchmaker-recheck/workspace/community-room-benchmark/evaluation/controls.jsonl` contains exactly four authored controls per case. However, `run.py:selftest` additionally grades `None` for case `crb-dev-001`, beyond those four distinct fixture outputs. Local preflight/control/selftest checks were repeated by root, reviewer and root after repair. Zero target launches is supported, but an unqualified claim that authoring validation used only four outcomes per case overstates the evidence. The malformed-output assertion is a harness check under a narrower interpretation of “control”; the request did not explicitly resolve that distinction. Report fixture counts and that extra assertion rather than silently assuming the looser budget meaning.

### Standalone export portability

The separately requested portability run now has enough native evidence to validate this path. Its isolated home has no Orchflows package or skill paths; `installed-identities.json` is empty. Ordinary built-in and unrelated plugin files were present, so this was specifically an **Orchflows-free** home, not an empty Codex installation. Neither native root nor reviewer made an Orchflows package read. The exported files match the repaired source export as decoded text; the harness's text copy normalized line endings, so they are not byte-identical exports.

Root `export-portability/.../rollout-2026-09-17T20-26-28-01a0b1e8-54a0-7523-9739-46923b87c0a8.jsonl` launches its single reviewer at line 29. The depth-one reviewer `rollout-2026-09-17T20-26-53-01a0b1e8-b799-7b63-a219-c7ad6b34ec89.jsonl` actually reads the standalone skill, process and bundled writing references, original memo and facts, verifies hashes, and completes at line 41. It makes no edits or delegation. Root repair is line 42 in the parent trace; verification and separately identified original/delivered evidence follow.

The output contains every supplied fact. Independently recomputed SHA-256 values match the native evidence: preserved memo `91373a152134f957a63b07143c1dfaacbd2e30918db7e81dcd4f945224123051`, facts `e3c5b59b5b7f54f0c656182849b74668ee74c76a8bda8d1bc95bd2e99ddc9520`, delivered memo `38ca9b1eeea9f3ceac364e62d5646e02bbe3b776434b03a391ed6818a9dd47ca`. This proves a successful standalone persistent-host path for this request. It does not rehabilitate the failed ephemeral trial or establish that every model/host will follow the process.

### Browser game: real output, skipped mandatory phase gate

**Process failure, despite useful runnable output.** The installed `browser-game/orchflows-home/libraries/3d-browser-game/skills/3d-browser-game/SKILL.md` is explicit: line 13 orders the core checkpoint before asset production; line 65 keeps final assets behind that checkpoint; lines 75–83 require a fresh core playtest and ready core decision; line 129 requires a new final reviewer. This is not a new inferred preference about staffing.

Native root `browser-game/.../rollout-2026-09-17T20-20-37-01a0b1e2-f98e-7351-b2c0-dda68ebf38ea.jsonl` reads that exact skill at line 30, then launches game and final-asset makers at 00:21:32.440 and 00:21:39.836 (lines 48 and 52). At 00:21:25 it incorrectly describes this initial parallel split as what the workflow requires. The workflow permits that split only after the core checkpoint. Asset production actually finishes at 00:23:34.519; no core reviewer was ever launched. The first and only reviewer is `final_reviewer`, launched at 00:30:29.105 (line 239). Thus later successful output cannot satisfy the omitted core gate retrospectively.

The final reviewer genuinely plays through ordinary rendered keyboard input, inspects screenshots, observes recovery/delivery/replay, and finds a dominant strategy: holding forward wins the risky route at full hull. Its native trace `rollout-2026-09-17T20-30-29-01a0b1ec-0116-77a3-93be-a10531f357f3.jsonl` completes at 00:33:09.122, before root's first repair attempt at 00:33:37.404. The subsequent successful patch and checks add a center obstacle and establish that straight-forward abuse now causes a setback. All three children are depth one, with no child delegation.

The actual final evidence does **not** demonstrate a successful delivery over either route after that collision/layout repair. `workspace/evidence/repair-record.md` and `verify-repair.mjs` cover the straight-forward failure regression; the final reviewer had already left safe-route completion unverified. Main skill line 135 also requires the main start–play–outcome–retry path after relevant changes. The final answer acknowledges safe-route uncertainty, but its opening “complete local prototype” and “repaired risky route was regression-tested” should not be read as demonstrated full mission completion on the delivered revision.

Classify this as model noncompliance with an already explicit phase dependency and incomplete final acceptance coverage. Blender output, integrated GLBs, actual rendering and the useful independent gameplay finding are supported. Full workflow conformance and completed post-repair gameplay are not. The 15-minute constraint authorized returning partial evidence; it did not authorize treating skipped gates as passed. Adding another layer of workflow prose is not justified by this single failure.

### Root report claim review

The draft `REPORT.md` correctly retains the original flat-orchestration and export ordering failures, the generated timestamp defect, and standalone portability limits. Before delivery it should also classify Browser Game as partial/process-failing, preserve the Benchmaker fixture-versus-validation budget qualification, and distinguish the failed ephemeral trial's host error from its separate decision to repair without an independent judgment. The earlier export timing uncertainty is now resolved for actual repair mutations by the table above. Design Loop continuation was outside this supplemental audit's assigned scope.
