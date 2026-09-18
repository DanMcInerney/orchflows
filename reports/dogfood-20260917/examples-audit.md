# Independent audit: wider dynamic and example runs

Inspected frozen installed instructions, source inputs, delivered artifacts and native traces for `dynamic-wide`, `social-search`, `evolve` and `benchmaker` under `C:/Users/danhm/orchflows-dogfood-20260917`. The first three runs completed. Benchmaker was still running when its final-review findings arrived at 00:20:36 UTC; its eventual repair and final handoff are outside this snapshot. No trial artifacts or source files were changed by this audit, and no agents were launched or continued.

The wider dynamic and Social Search runs demonstrate actual useful fan-out and gathering. Evolve demonstrates a rejected regression, versioned evaluator repair, then a confirmed numeric improvement within two rounds. Benchmaker exposed the central architectural failure: its no-history pilot incorrectly activated the dynamic fallback inside a child and launched a grandchild.

## Wider dynamic workflow

The root chose two maker assignments, each owning three separate branch output directories. `make_nse` ran from 00:09:31 to 00:10:46; `make_wch` ran from 00:09:37 to 00:10:38. The executions overlap for approximately a minute. After both returned, the root created the joined portfolio at 00:11:00 and launched one whole-result reviewer at 00:11:06. The reviewer finished at 00:11:45; the root returned at 00:11:50. No maker assigned work or launched another agent. The stable pack was not repaired during review.

I independently recalculated every vendor/branch total using Decimal arithmetic from the original quotes and monthly usage. All 18 CSV totals match. All six branch decisions are below 250 words. Correct selections are North/Birch $2,040, South/Aster $1,496, East/Birch $2,400 and Harbor/Birch $2,040; West and Central have no affordable eligible quote. The total is **$7,976**. The portfolio preserves retention, CSV-export, annual-prepayment and provisional-overage conditions. Its source-preservation limitation is disclosed rather than silently treated as verified history.

This demonstrates flexible staffing and integration, not an optimal worker count or a measured speedup over sequential execution. The prior smaller tasks used zero or one maker; this wider task used two concurrent makers without a workflow rewrite.

Evidence: `dynamic-wide/workspace/outputs/portfolio.md`, six adjacent branch directories, and root trace `dynamic-wide/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-08-57-01a0b1d8-4d3b-7381-819d-b5f8f93add11.jsonl` under the scratch root above.

## Social Search

Two source collectors ran concurrently. GitHub used two search targets and two issue-read targets; Hacker News used one search target, two batch-read targets and one further direct read. Each consumed exactly its four-target allowance, including failed/empty reads. All acquisition tool calls occurred between 00:10:07 and 00:10:18 UTC, within the three-minute acquisition window even measured from the first dispatch at 00:09:47. No new acquisition was performed by the assessor.

The GitHub collector finished at 00:11:01 and HN at 00:11:08. Only afterward, at 00:11:19, the root launched the independent evidence assessor. It wrote `uv-social-search/assessment.md` at 00:12:20 and finished at 00:12:26. The root read that file and returned its same substantive four-part ranking with a link to the complete assessment. No root edit to the assessor's file or second review is present. Collector ownership remained separate; no child delegated.

The final assessment accurately distinguishes the narrow inspected evidence from prevalence, preserves the GitHub reply-rendering limitation, HN access failures, lack of retained 2026 material, and relevant counterevidence. The two retained GitHub issues and one HN discussion fit the requested publication window. I checked the tool-call ledger and collected/assessed artifacts; I did not perform a new source census or independently establish present-day uv behavior. The run supports the bounded collection-and-ranking process, not comprehensive topic coverage.

Evidence: `social-search/workspace/uv-social-search/{github/results.md,hacker-news/results.md,assessment.md}` and root trace `social-search/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-08-59-01a0b1d8-5297-7fd2-a389-e20d8b7b643b.jsonl`.

## Evolve

The root preserved the original and froze evaluation v1 before making a challenger. Round 1 passed its initial cases and showed a large speed gain, but a fresh reviewer found changed behavior for asymmetric equality on custom hashable objects. The root rejected that candidate. It versioned the evaluator to v2, kept v1 evidence, and added the discovered regression before the second experiment.

Round 2 narrowed the optimization to exact built-in lists/tuples containing exact integers; other inputs execute the original loop. A distinct reviewer checked the frozen candidate, reran the numeric evaluator, and added exhaustive integer and targeted fallback comparisons. Its final arrived at 00:17:19; the root recorded the decision at 00:17:33 and promoted at 00:17:45. The checkpoint records exactly two attempted rounds, zero remaining, and the requested bound as the stop reason. No child delegation or extra challenger round occurred.

My separate 105-input comparison against the preserved original passed. The promoted source matches the retained round-2 candidate exactly. Saved raw round-2 samples support the recorded approximately 258x median improvement; the final approximately 295x claim comes from the later final verification measurement. These are local measurements on one integer workload, not a general performance guarantee. Sequential baseline/candidate timing and the deliberately narrow optimization are limitations.

The numeric reviewer was **not blind**: its own line-17 read includes the original path, round-2 plan and prior round's review. However, the blinding restrictions appear in the workflow reference's “Generated judge prompt” section; the numeric-improvement section separately requires exact artifacts, scoring code, raw baseline/candidate samples and requirements checks. This was a numeric rule (>2x plus compatibility and regression audit), not subjective preference selection. I therefore do **not** classify the exposure as a proven failed gate or demand another subjective judge. The wording's scope is ambiguous if blind numeric audits were intended. The observed process supports an independent, non-blind metric audit.

Evidence: `evolve/workspace/evolve-runs/duplicate-finder/` (both evaluator versions, experiments, measurements and checkpoint), and reviewer trace `evolve/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-16-14-01a0b1de-f6d7-77f0-9a8a-a0b196370157.jsonl`.

## Benchmaker: confirmed root-only dispatch violation

The pilot started correctly with `fork_turns="none"` at 00:14:45. Before disclosure, its only input reads were the two public case JSON files. It saved answers at 00:15:18 and notified the root before its continuation at 00:15:27. Its initial context contains no authoring transcript. This is instruction-level isolation, not filesystem security.

On continuation, the pilot explicitly decided to apply the dynamic fallback:

- At 00:15:31 it announced a “general orchestration workflow” with an independent final review.
- At 00:15:33 it read installed `orch-dynamic-workflow/SKILL.md`.
- At 00:15:38 it read core `docs/architecture.md`, including the root-only execution rule.
- At 00:17:23 it launched `/root/public_audit/audit_report_review`.
- At 00:18:41 it also sent that grandchild a further message.

Native metadata independently identifies the new agent's depth as **2**, with the pilot as parent. This violates the user's core requirement and the installed architecture. The root noticed and interrupted the grandchild at 00:18:51, then directed the pilot to finish. The pilot documented its mistake. Its report now explicitly acknowledges that its original assignment prohibited delegation, so this is not adequately explained as a missing restriction from the dispatcher. Assignment payloads remain encrypted, preventing a verbatim instruction comparison, but the child's own admission and instruction reads support the conclusion.

The failure mechanism is fallback selection inside an already-delegated assignment: the child treated its local audit task as a fresh top-level workflow. The host skill catalog exposes dynamic fallback to children, and the entrypoint does not state top-level eligibility directly. A short root-only eligibility guard in the dynamic entrypoint/description is a proportionate correction; duplicating the entire architecture in every library would not address the selection point cleanly. A fresh no-history-child trial is needed to test any correction. The interrupted run remains a failure of flat dispatch regardless of later package quality.

Exact evidence: `benchmaker/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-14-45-01a0b1dd-9b28-7db3-8bc4-a2c169e8757e.jsonl`, lines 40–50, 84–86, 111 and 123–133. Grandchild metadata: `rollout-2026-09-17T20-17-23-01a0b1e0-0451-7cc2-90e5-1a164f2483e2.jsonl` in that same directory.

## Benchmaker: public contract, budgets and unfinished validation

The pilot's two frozen answers were reasonable schedules but used the wrong serialization schema and scored **0/2**. The actual phase-1 scope withheld README, which defines the required `schedule` schema; neither authorized public JSON file carries that contract. The package's own audit plan says README should be provided. The pilot documented the missing schema before disclosure, and the grader rejects the unchanged answers afterward. This is a real audit setup/package input-contract defect, not demonstrated scheduling inability. It also affects a future target receiving only the documented per-case input.

No candidate or representative target launch occurred in the inspected execution. The zero-launch refusal command returned before subprocess execution. All four authored control fixtures per case passed. The auditor additionally tried malformed/stale/time answer variants outside that fixture set, and the unintended grandchild repeated boundary checks. If “four control outcomes per case” limits all authoring-validation variants, the cap was exceeded for dev-02; if it only caps stored authored fixtures, the file-level count is respected. Preserve this budget ambiguity rather than claiming universal compliance. The two-case independent public audit count itself was not expanded.

After gathering the pilot report, the root launched a distinct final package reviewer with `fork_turns="none"` at 00:19:24. At 00:20:36 it reported material validity gaps, including the missing public contract and acceptance of meaningless explanation text. No package repair preceded this separate review in the trace inspected. Those findings and any repairs were still being handled at this snapshot. This audit therefore makes no claim that Benchmaker's final package, final metadata or eventual repaired grader passes.
