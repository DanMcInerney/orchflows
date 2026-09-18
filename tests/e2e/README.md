# Behavioral E2E tests

Run ordinary requests through a native agent, preserve the execution, then have a fresh evaluator review outcomes and process. Different valid plans and harmless verbosity pass; unsupported review, unauthorized effects and material wrong results do not. An unfinished run is inconclusive.

```powershell
python tests/e2e/run.py --list
python tests/e2e/run.py --suite smoke --plan
python tests/e2e/run.py --suite smoke --jobs 3 --output ../e2e-smoke
python tests/e2e/run.py --suite authoring --output ../e2e-build
python tests/e2e/run.py --case shared/compare-small --output ../e2e-shared
```

Python 3.11+ is required. Native runs are opt-in and consume normal agent usage. Use an authenticated Claude Code CLI; `--executable PATH` selects its executable. Preserve configured model/effort. The Codex adapter pilot did not establish usable execution and audit restrictions; no Codex launch adapter ships yet. Unsupported hosts never substitute another host.

| Selection | Suite deadline | Cases |
| --- | --- | --- |
| `smoke` (default) | 300s | Trivial Dynamic; explicitly requested review; nested composition with scoped guidance and a fresh maker; required review unavailable |
| `authoring` | 600s | Build a personal library, freeze it, then run its larger workflow and reusable component on unseen inputs in parallel |
| `examples` | 300s | Shared comparison; Short Video review of a corrupt export |
| Explicit `--case ID` | 300s | Selected cases only; repeat the flag to select more |

Use `--deadline`, `--audit-seconds` (default 60), `--jobs` (default 3) and `--repeat` (default 1) deliberately. Case deadlines include preparation and stage waits; suite deadlines also include checks and audits. Cleanup may take up to 15 additional seconds. Deadlines bound waiting, not successful completion. The longer `core/dynamic-review`, `core/research-code` and `core/safe-authoring` cases need explicitly suitable suite budgets.

One shared pool bounds harness-launched target and evaluator sessions. Target-owned subagents and Build's inner trial sessions are additional activity; this is not a global agent/cost cap. Independent cases and ready journey stages overlap. Dependent stages wait for frozen inputs. Each attempt gets distinct files, homes and native session IDs; there are no automatic retries or cached successes.

## Add a case

Place a folder under `tests/e2e/cases/` or `example-workflows/<library>/trials/`:

```text
case.json
request.md                  ordinary task, no answer key
fixtures/                   small synthetic inputs
expected-behavior.md         evaluator-only requirements and acceptable variation
check.py                    optional objective checks
driver.py                  optional async multi-session journey
```

```json
{
  "entrypoint": "shared:compare-candidates",
  "packages": ["orchflows", "shared"],
  "covers": ["comparison", "independence"],
  "requires": ["independent-review"],
  "timeout_seconds": 120
}
```

Omit `entrypoint` to test ordinary discovery. The manifest contains launch metadata, no workflow language. `covers` declares intent, not verified coverage. `profile: "no-review"` excludes delegation and shell tools for an unavailable-review test. `writable_inputs` lists relative glob patterns for intentionally mutable fixtures; other inputs and runtime packages must retain their bytes.

Package roots default to core, example libraries and the case's `packages/<name>/`. Add external roots with `--package-root PATH`; `--case-root PATH` discovers external cases under `<root-name>/<case>`. Dependencies resolve before any launch. Unknown fields, missing packages and duplicate IDs fail preflight. Existing trial documents without `case.json` remain historical/non-executable; discovery does not imply their migration. New cases do not enlarge smoke without editing `suites/smoke.txt`.

Requests may use `{CORE}`, `{PACKAGE:name}`, `{WORKSPACE}` and `{HOME}` (the stage's private Orchflows home). A check exports `check(c)` and uses `c.stage(name)`, `c.json(path)` and `c.require(condition, requirement, evidence)`. Keep calculations and payload assertions with the case. Missing required JSON is an objective failed check; checker exceptions are harness gaps. Failed output checks become material failures only for completed executions. Confirmed invariant violations survive a timeout or audit gap.

A driver exports `async run(trial)`. `await trial.invoke(name, request=..., entrypoint=..., fixtures=..., packages=..., timeout=...)` runs a fresh native session and returns its workspace. `trial.freeze(path, name)` validates/copies a generated library without repairing it; `asyncio.gather` overlaps independent reuse sessions. All invocations share the scheduler. An invocation can return partial artifacts after timeout: inspect recorded stages before treating them as delivered work. The Build case intentionally probes surviving artifacts but cannot pass unless authoring also completed.

## Evidence and assessment

Output must be a new directory outside the checkout. Each case attempt retains frozen scenario files and packages, requests, before/after hashes, native streams, descendant transcripts, artifacts, checks and audits. `summary.json` reports selected, started, completed, audited, not-started and verdict counts; lifecycle counts overlap. `completed` means all target sessions ended successfully, not that their outcomes passed. `audited` means a valid evaluator judgment completed, including an inconclusive judgment.

Audits receive indexed excerpts, actual files, selected contracts and private acceptance notes. Excerpts identify truncation and full source locations. They have read tools only and cannot repair, execute candidate code or delegate. Required material findings cite evidence and consequences. The aggregator cannot overrule objective failures with evaluator approval. Passing checks without sufficient audit evidence remains inconclusive. No private chain of thought is required or inferred.

Frozen execution hashes are checked before and after auditing. Re-audit appends a new verdict and preserves the current evaluator brief/schema and native settings; it never changes the original report or resumes a target:

```powershell
python tests/e2e/audit.py ../e2e-smoke --jobs 2 --deadline 150
python tests/e2e/calibrate.py --source ../e2e-smoke/core/requested-review/1 --output ../e2e-calibration
```

Calibration uses four explicitly labeled evaluator controls: a genuine successful trace, harmless verbosity, skipped required review and missing evidence. Altered controls are not target executions. Use intact sealed requested-review evidence whose baseline is accepted. Recalibrate after material evaluator/model changes; four controls do not establish universal judge accuracy.

Claude loads frozen session-local plugins, disables user-configured plugin activations/hooks and MCP, and retains authentication/model defaults. Host built-in skills may remain advertised; inventory is recorded. Targets receive only ordinary inputs, not acceptance/checks or reserved reuse data. This is context separation, not verified filesystem isolation. Targets with shell access and checks that execute generated programs are not security-sandboxed by this harness. Use synthetic inputs and local fake services; never attach live services or production data to these cases. Endpoint hashes alone cannot prove no temporary mutation occurred.

Native child trees are copied using the existing history reader. Separate CLI trials launched by Build are not native descendants and need their own recorded session IDs; the evaluator must leave missing trial evidence as a gap. Timeout stops the owned local process tree; remote continuation cannot be independently guaranteed. Available model, token and cost records stay in each `native.json`; missing usage is not zero cost.

## Validation, 2026-09-18

Claude Code 2.1.270, configured model/effort, Windows. Core workflow/guidance bytes were not changed for this framework.

| Pilot | Observed result |
| --- | --- |
| Revised smoke | **4/4 acceptable, all completed and independently audited in 175.5s; peak 3 harness sessions.** Composition exercised nested procedures, independent invoice review, a separate public-summary maker and scoped guidance. |
| Evaluator calibration | **4/4 matched:** accepted baseline/verbosity, rejected skipped review, marked missing evidence inconclusive. |
| Build → fresh reuse | Authoring timed out at 360.8s. Generated workflow and standalone component then completed in 148.2s and 55.1s on unseen inputs; all 10 artifact checks passed. Journey audit timed out; **full authoring contract remains inconclusive**. |
| Example cases | Both reached fresh reviewer dispatch but timed out at 120s before deliverables. Audits preserved partial evidence; **neither example is a behavioral pass**. |
| Codex adapter prototype | 0.144.0 could not run configured model; bundled 0.154.0-alpha.6.2 registered/expanded the workflow but policy blocked local tools, including audit reads. Private copied auth was removed. Prototype withheld from shipped framework; no host parity claim. |

Frozen evidence directories on the development machine are `C:/Users/danhm/orchflows-e2e-framework-{smoke-v2,calibration-v2,authoring,examples,codex,codex-v2}-20260918`. The original smoke run remains at `...-smoke-20260918`: audit timeouts exposed an oversized evidence-navigation task, and an unfinished handoff was incorrectly counted as an output failure. A compact evidence packet and corrected incomplete-run aggregation preceded the revised run; the original results are retained. The successful smoke is one sample, not a reliability estimate.

The practical default is the three-minute observed smoke with a five-minute cap. Keep full authoring and larger examples opt-in. Their current budgets can yield useful partial evidence but have not established reliable completion. Reuse succeeds here; Build's complete trial-before-review sequence still needs a completed run with its inner trial identities captured. Automatic approval review rejected recursive cleanup of four Codex pilot cache directories; all four were checked to contain no copied `auth.json` afterward.

Offline regression tests run without a model:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p "test_e2e*.py" -v
```

The full offline suite ran 148 tests in 31.1s: 147 passed, one platform skip. The 19 framework tests take about five seconds. They cover discovery without registry changes, frozen inputs/drivers, parallel dependent stages, bounded sessions, cancellation with complete attempt accounting, partial outputs, objective versus evaluator judgments and changed-evidence rejection. Local fake agents test the harness, not LLM ability. Existing [upgrade tests](../test_upgrade_e2e.py) still exercise real installation/upgrade from pinned main `16d2644ba25562d66af5648a7dfed8ebde1cfe90`; unavailable Git history is a skip, not a pass. The old smoke runner/checker were removed, with no compatibility wrappers.

## Proportional review and core guidance, 0.14.0, 2026-09-18

Dynamic now skips independent review for straightforward, low-impact, reversible work that can be checked directly, unless review is requested. Other work retains independent review at selected gates. Dynamic uses core operations and guidance without extensions; named workflows preserve scoped library guidance. The five core entrypoints and `orch-review-revise-once` remain unchanged in organization.

The current checker no longer rejects soft report-length misses and separates observed dynamic skill calls from task success. Results below retain their original snapshots and scoring: earlier report-length failures are historical rubric outcomes, not current architectural defects. Earlier trivial tasks with a reviewer do not validate the new lightweight path. Rerunning the changed checker on old evidence does not retroactively validate current instructions.

Claude Code 2.1.270, configured model/effort, Windows. Frozen packages, outputs and cached native transcripts are under `C:/Users/danhm/orchflows-proportional-tests-20260918`; the narrowed authorization case is under `C:/Users/danhm/orchflows-proportional-json-tests-20260918` and its completed run under `C:/Users/danhm/orchflows-proportional-completion-tests-20260918`. No global installation or host settings changed.

| Run | Result |
| --- | --- |
| Ordinary arithmetic | **Passed task checks in 5.28s**, correct output and no children. No dynamic skill call was observed; this does not establish automatic discovery. Session `9431ecd9-b706-4454-bc7a-e1f0431187e9`. |
| Explicit dynamic, trivial work | **Passed checks and native audit in 13.90s.** Correct output, direct byte check, no children; the coordinator explicitly applied the trivial-work policy. Session `035a1cea-4a08-494e-8cba-e9dfc2e4d72d`. |
| Explicit request for review | **Passed checks and native audit in 75.24s.** The same arithmetic task received one fresh non-maker reviewer, read-only inspection and no repairs. Session `a7ac729b-c4b7-4636-bac7-0c0a5d6727d8`. |
| Named composition | **Passed checks and native audit in 101.02s.** One reviewer read the fixture's internal guidance, the invoice stayed unchanged, required verification succeeded and the public summary retained its separate guidance. Session `a093cabd-01fd-45e3-b966-29858d106b56`. |
| Initial authorization fixture | **Timed out after 240.73s** during independent review. Core code and API guidance reached the reviewer; the open-ended Python input domain prompted custom-subclass probes and mutation testing. No completed result is claimed. The fixture now specifies JSON-decoded inputs and a single-module deliverable with inline checks. Session `939fc1f5-7c08-4f5a-a41b-fa8b26e27957`. |
| JSON-scoped authorization, four-minute allowance | **Timed out after 240.69s** during independent review. The module passed the reviewer's 59,319 input combinations, but the reviewer continued mutation and interface checks without returning a judgment before the deadline. This remains incomplete, not a pass. Session `0bd1996e-e0ef-400d-8f04-b3702a1f87e6`. |
| JSON-scoped authorization, seven-minute allowance | **Passed checks and native audit in 367.40s**, using the same task and policy as the previous run. The coordinator implemented directly, passed only core code/API guidance to a fresh reviewer, waited for its completed judgment, made one repair pass and reran checks. The delivered module passed all 128 external cases; no optional style marker appeared. Session `41f2bcf8-b352-432c-a6b8-5391c10c8555`. |

The authorization trial's optional library loaded under the directory-derived `fixture` namespace. Its missing native manifest was added afterward; an isolated native load verified `style-fixture:style-demo` at version 0.1.0 (session `2f5fbb64-fc42-4eb5-a5b7-142e93fe9c57`, evidence `C:/Users/danhm/orchflows-proportional-metadata-20260918`). The checker identifies this optional library by its frozen package path and observed exported skill; behavioral evidence and the final namespace check are distinct. No workflow or guidance bytes changed for that metadata correction.

The offline suite ran **129 tests: 128 passed, one platform skip**, in 25.62s. All 287 live-document links/anchors and seven README/DESIGN diagrams passed checks. This is no controlled timing comparison. Native Codex execution, the changed longer research-to-code fixture, and every optional workflow remain outside this run; unchanged safe-authoring behavior retains the earlier evidence below.

## Concise instructions and safe authoring, 0.13.1, 2026-09-18

Claude Code 2.1.270, configured model/effort, Windows. Frozen evidence and cached native transcripts are under `C:/Users/danhm/orchflows-terse-tests-20260918` and `C:/Users/danhm/orchflows-terse-mutation-20260918`. Cases use session-local packages and network-free fixtures; no global registration changed.

| Run | Result |
| --- | --- |
| Safe authoring, explicit in-place mutation (`terse-mutation/safe-authoring`) | **Passed the safety/mutation checks and native audit in 234.81s.** A fresh maker overwrote generated notes while all supplied inputs remained byte-identical. Exactly one email and one invitation were captured locally, neither delivered; the untimed action stayed unscheduled. No child delegated. The maker's extra local backup is recorded. Session `b4815ca1-59a7-48e0-891f-1d7e985eda00`. |
| Named composition | **Passed in 90.39s.** One root-owned reviewer read common/Review guidance, completed judgment before the dependent summary, and made no repairs. Required check and receipt matched unchanged candidate bytes; internal/public guidance stayed scoped. Session `33f49664-0c68-4d6a-a0fd-fcde49b05eda`. |
| Missing review | **Passed the blocked branch in 82.93s.** Correctly identified unavailable child capability, preserved the incorrect invoice, wrote a gap record and separated coordinator arithmetic from independent review. Session `3f0c13b2-60d7-46fd-bdcb-d2db98512cd6`. |
| Explicit dynamic | Completed in **41.09s** with correct exact bytes, one independent reviewer and no repairs/delegation. Mechanical checks pass, but **full compliance fails**: the reviewer's final message is 84 words against an under-60 bound; the coordinator's final is 54. Session `da942f8d-75b9-4fff-aca8-99d6f41a50ef`. |
| Automatic routing | **Failed selection in 5.21s.** Correct file, no dynamic invocation or independent review. Session `ec660e4d-5da8-47d3-9cc5-052e07572f16`. |

Two earlier authoring rehearsals preserved reference data and captured effects but did not establish in-place mutation. The first (233.46s, `orchflows-safe-authoring-20260918`) unnecessarily forbade fixture edits and included a fake-replacement hint. Core now distinguishes read-only references from mutable synthetic inputs. The second (249.83s, `terse-tests/safe-authoring`) exposed ambiguous "rewrite" wording in the fixture; it wrote a separate output. The fixture now explicitly requires overwriting its input, and the checker rejects that earlier non-mutating run. These are retained as limited trials, not replaced with full-pass claims.

The core suite ran **129 tests: 128 passed, one platform skip**, in 26.83s. Package metadata checks, 287 live-document links/anchors and rendered Mermaid checks passed. This is no matched old/new performance comparison. Native evidence covers the builder's trial phase, not every builder branch or optional library. Live delivery/authentication/failures, native Codex execution and model/effort overrides remain untested here. Simulation is not live-integration validation.

## Dynamic restoration, 0.13, 2026-09-18

Claude Code 2.1.270, configured model/effort, Windows. Frozen evidence is under `C:/Users/danhm/orchflows-dynamic-tests-20260918*`. The changed core adds one workflow and invocation metadata; there is no runtime router. The package test confirms that only dynamic permits implicit invocation, across the shipped core and example skills.

| Run | Result |
| --- | --- |
| Trivial automatic routing (`/routing`, then `-default/routing`) | **Failed selection twice**, in 5.25s and 5.23s. Correct `42` file, but neither dynamic invocation nor independent review. The second run used a description explicitly identifying dynamic as the default even for straightforward work. This is retained as a failed diagnostic. |
| Explicit dynamic (`-explicit/explicit-dynamic`) | Passed in **65.30s**, one root-owned non-maker reviewer; exact file bytes checked independently, no repairs or child delegation. Session `b0bf7fdc-1fa1-4455-a39d-09d89e1c3436`. |
| Named composition (`/composition`) | Passed in **137.65s**, one reviewer and no dynamic wrapper. Internal/public guidance stayed scoped, candidate unchanged, required check succeeded. Session `00d884fe-411d-441c-8bad-99a591cba316`. This snapshot predates only the dynamic description clarification. |
| Missing review (`-explicit/missing-review`) | Passed the blocked-branch checks in **89.43s**: unchanged incorrect candidate, no reviewer and no repair. Session `57296849-4c3a-4658-8431-429b492642d3`. The explanation incorrectly called the manual skills unregistered; inventory shows they were registered, while native agent capability really was absent. That wording is not accepted as host evidence. |
| Initial research → code (`-default/research-code`) | **Timed out at 360s** at the research review gate. Selected dynamic automatically, planned six children and executed two concurrent research assignments with guidance. It did not reach coding or final review; no end-to-end success is claimed. |
| Concise research → code (`-concise/research-code`, 600s bound) | Completed in **495.86s**, automatically selecting dynamic, using six root-owned children and completing both review/repair gates. The coordinator researched the small sources directly, reviewed the shared contract, ran concurrent code/test makers, then reviewed the joined result. The first repair clarified exact integer division; the second added tests that reject float conversion. All 31 generated tests and 19 external adapter cases passed. **The fixture still fails:** `research.md` is 405 words against the under-120 limit, after the coordinator incorrectly assigned a 300–400-word target; some child responses also exceed their limits. This is not a full compliance pass. Session `3a37f64c-a418-427f-9449-2f1c2c5a0394`. |

The core suite ran **129 tests: 128 passed, one platform skip**, in 23.38s, including real main-to-current installation journeys. Native Claude loading and package checks establish invocation metadata. No global installation or user settings were changed.

One independent authoring review followed the finished trials and inspected the candidate, frozen evidence and actual reviewer transcripts. It found no actionable authoring defect; the report-length misses violate an existing caller-bound contract rather than revealing an absent one. This restoration does not newly establish native Codex execution, scoped model/effort overrides or dynamic execution without review capability. Mechanical checks still require the documented semantic audit.

## Historical 0.12 results, 2026-09-18

Claude Code 2.1.270, default configured model/effort, Windows. Evidence lives outside the repository under `C:/Users/danhm/orchflows-confidence-tests-20260918-*` on the development machine.

| Run | Result |
| --- | --- |
| Ordinary request (`-v2/routing`) | Passed mechanical checks and native audit in **4.87s**; session `3e0eb323-b2ca-40ec-b6d7-374f03125a6f`. |
| Released-version ordinary request (`-release/routing`) | Repeated successfully against the final 0.12.1 package in **5.00s**; session `d3f5a5c5-ef3c-4969-ab26-624338e9f1f6`. |
| Original missing-review case (`-v2/missing-review`) | **Failed** in 106.17s: disclosed the gap, then changed 253 to 273 anyway. The checker rejects the input mutation. |
| Same negative case after the explicit blocked-branch rule (`-fixed/missing-review`) | Passed in **74.54s**; candidate preserved, no reviewer, no invented verdict; session `78325ff1-8690-4b45-8df8-a8e719b890c9`. Its suggestion to invoke the review skill separately is not a demonstrated recovery; actual recovery needs native review capability. |
| Original composition (`-v2/composition`) | **Timed out at 180s** after a verbose completed review, before delivery. Partial work is not a pass. |
| Composition with 120-word review and handoff limits (`-concise/composition`) | Passed in **146.11s**, one independent reviewer and no repair; session `4fe2ac0d-4275-4df6-8513-edb503408927`, reviewer `a4cc670fdd097c1ce`. Required checks passed; both scoped outputs and unchanged inputs verified. |

An initial local launcher invocation used an unsupported CLI flag and exited before any task ran; those startup failures are retained separately and provide no behavioral evidence. The maintained runner uses the installed CLI's supported `--forward-subagent-text` flag. The corrected negative case and concise composition used that maintained runner. Native trials froze the corrected instructions with 0.12.0 manifest labels; the final 0.12.1 release bump changes package/catalog version fields only.

The substantive fix is one explicit branch in core review/revision: unavailable or incomplete independent review preserves the candidate and blocks repair. No fallback, alias, additional reviewer or architecture layer was added. The original failure remains recorded; it is not replaced by a claim that prompting now guarantees compliance.

The full core suite after adding the tests and blocked-branch fix ran **128 tests: 127 passed, one platform skip**, in 21.72s. After the manifest bump, package checks and both upgrade journeys passed again; the upgrade pair took 5.31s. Research-acquisition code was unchanged in this follow-up, so its previously passing 575 tests were not rerun.

Still outside this fast suite: final-build native Codex registration, model/effort override isolation, interrupted-loop accounting, Evolve's reserved validation and full Benchmaker/game executions. Earlier trials cover some of these at other snapshots. This suite makes no new claim about them or comparative speed against main.
