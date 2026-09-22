# Behavioral E2E tests

Run ordinary requests through a native agent, preserve the execution, then have a fresh evaluator review outcomes and process. Different valid plans and harmless verbosity pass; unsupported review, unauthorized effects and material wrong results do not. An unfinished run is inconclusive.

```powershell
python tests/e2e/run.py --list
python tests/e2e/run.py --suite smoke --plan
python tests/e2e/run.py --suite smoke --jobs 3 --output ../e2e-smoke
python tests/e2e/run.py --suite authoring --output ../e2e-build
python tests/e2e/run.py --case shared/compare-small --output ../e2e-shared
```

Python 3.11+ is required. Native runs are opt-in and consume normal agent usage. Use an authenticated Claude Code or Codex CLI; `--host claude|codex` and `--executable PATH` select the host and executable. Configured model/effort settings pass through unchanged, but the host decides what applies; evidence records the observed model and effort. Native controls need validation on the selected host/version; unsupported hosts never substitute another host.

The [gate study](gate-study.md) proposes comparisons of work-unit boundaries and Build/Dynamic authoring paths across a 31-family development matrix. Its opt-in `gates` and `gates-authoring` suites add six executable diagnostics with offline scorer controls; `gates-regressions` adds the blocked-authoring prerequisite case and requested-review calibration source. See the [predictions](gate-predictions.md) and [native pilot results](gate-results.md) for the executed subset and limitations. Smoke membership is unchanged.

The [next-stage study](next-stage-study.md) adds six cases for joined multi-guidance review, ordinary research/code and survey requests, a compatible API change, and direct versus saved release briefs. A separate two-case probe compares the current Dynamic exception with review for every unit. `python -B tests/e2e/next_stage.py --suite next-stage --output ../next-stage-prepared` freezes predictions, cases and runtime packages without model calls. Native execution is explicit and API-only; see the study for bounds and authentication. These cases have offline scorer controls, **not new native results**.

| Selection | Suite deadline | Cases |
| --- | --- | --- |
| `smoke` (default) | 300s | Trivial Dynamic; explicitly requested review; nested composition with scoped guidance and a fresh maker; required review unavailable |
| `authoring` | 600s | Build a personal library, freeze it, then run its larger workflow and reusable component on unseen inputs in parallel |
| `examples` | 300s | Shared comparison; Short Video review of a corrupt export |
| Explicit `--case ID` | 300s | Selected cases only; repeat the flag to select more |

Use `--deadline`, `--audit-seconds` (default 60), `--jobs` (default 3) and `--repeat` (default 1) deliberately. With `--repeat k`, `summary.json` `cases` gives each case's attempts, assessment counts and `all_acceptable` (pass^k), and the evidence README adds a line per case; single attempts are weak evidence of reliability. Case deadlines include preparation and stage waits; suite deadlines also include checks and audits. Cleanup may take up to 15 additional seconds. Deadlines bound waiting, not successful completion. The longer `core/dynamic-review`, `core/research-code` and `core/safe-authoring` cases need explicitly suitable suite budgets.

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

The default `local` profile gives Codex workspace-write access with shell network access disabled. Opt into `profile: "authoring"` when the target must launch a separate native CLI trial whose model calls require network access. Codex keeps the same tools and filesystem boundary, adding `sandbox_workspace_write.network_access=true` for that invocation. This grants general shell network permission, not an endpoint allowlist: trial requests must still forbid task-facing external effects and use local fakes. Claude's `authoring` profile has the same tools as `local`; neither profile adds a shell/network sandbox there. `no-review` does not enable network, and audits retain their separate restricted profile. No profile changes global settings or registration.

Package roots default to core, example libraries and the case's `packages/<name>/`. Add external roots with `--package-root PATH`. An explicit root replaces a default root with the same package name, so matched old/new trials can run from one harness; `--plan` and `plan.json` list each `package_overrides` entry, and two explicit roots with one name fail preflight. `--case-root PATH` discovers external cases under `<root-name>/<case>`. Dependencies resolve before any launch. Unknown fields, missing packages and duplicate IDs fail preflight. Folders without `case.json` are manual trial specifications; the runner does not execute them. New cases do not enlarge smoke without editing `suites/smoke.txt`.

Requests may use `{CORE}`, `{PACKAGE:name}`, `{WORKSPACE}`, `{HOST_CLI}` and `{HOME}` (the stage's private Orchflows home). A check exports `check(c)` and uses `c.stage(name)`, `c.json(path)` and `c.require(condition, requirement, evidence)`. Keep calculations and payload assertions with the case. Missing required JSON is an objective failed check; checker exceptions are harness gaps. Failed output checks become material failures only for completed executions. Confirmed invariant violations survive a timeout or audit gap.

A driver exports `async run(trial)`. `await trial.invoke(name, request=..., entrypoint=..., fixtures=..., packages=..., profile=..., timeout=...)` runs a fresh native session and returns its workspace. `profile` defaults to the case's profile and may be selected per stage, so only an authoring stage needs the network opt-in. `trial.freeze(path, name)` validates/copies a generated library without repairing it; `asyncio.gather` overlaps independent reuse sessions. All invocations share the scheduler. An invocation can return partial artifacts after timeout: inspect recorded stages before treating them as delivered work. The Build case intentionally probes surviving artifacts but cannot pass unless authoring also completed.

## Evidence and assessment

Output must be a new directory outside the checkout. Each case attempt retains frozen scenario files and packages, requests, before/after hashes, native streams, descendant transcripts, artifacts, checks and audits. `summary.json` reports selected, started, completed, audited, not-started and verdict counts; lifecycle counts overlap. `completed` means all target sessions ended successfully, not that their outcomes passed. `audited` means a valid evaluator judgment completed, including an inconclusive judgment. Each `report.json` and summary result carries `observed` models and efforts, tallied from the native records of every target agent; audit packets show each agent's tallies.

Audits receive indexed excerpts, actual files, selected contracts and private acceptance notes. Excerpts identify truncation and full source locations. Auditors must not repair, execute candidate code or delegate. Claude exposes read tools only; Codex uses a read-only sandbox with shell reads available and native delegation disabled. Required material findings cite evidence and consequences. The aggregator cannot overrule objective failures with evaluator approval. Passing checks without sufficient audit evidence remains inconclusive. No private chain of thought is required or inferred.

Frozen execution hashes are checked before and after auditing. Re-audit appends a new verdict and preserves the current evaluator brief/schema and native settings; it never changes the original report or resumes a target:

```powershell
python tests/e2e/audit.py ../e2e-smoke --jobs 2 --deadline 150
python tests/e2e/calibrate.py --source ../e2e-smoke/core/requested-review/1 --output ../e2e-calibration
```

Calibration uses four explicitly labeled evaluator controls: a genuine successful trace, harmless verbosity, skipped required review and missing evidence. Altered controls are not target executions. Use intact sealed requested-review evidence whose baseline is accepted. Recalibrate after material evaluator/model changes; four controls do not establish universal judge accuracy.

Claude loads frozen session-local plugins, disables user-configured plugin activations/hooks and MCP, and retains authentication and model/effort settings. It records the requested effort sources it finds (`CLAUDE_CODE_EFFORT_LEVEL`, `effortLevel`, `modelSettings`) and reports a gap when the root session's recorded effort differs from the requested value (the host decides which request applies; a top-level user `effortLevel` does not apply to Opus 5.5); an audit keeps its verdict and records such condition gaps as observations; `modelSettings` is recorded but not interpreted. Host built-in skills may remain advertised; inventory is recorded. Codex uses complete package copies under each workspace's `.agents/skills`, checks native discovery, and passes configured model/effort through without changing global registration, reporting a gap when `turn_context` differs. Its targets request workspace-write; audits request read-only and disable native delegation. Audit shell subprocess delegation is not independently filtered; sandbox enforcement needs a host-specific probe. Use `--executable` when the CLI on PATH is older than the configured model requires; the observed models show which model actually ran.

Targets receive only ordinary inputs, not acceptance/checks or reserved reuse data. This is context separation, not verified filesystem isolation. Targets with shell access and checks that execute generated programs are not security-sandboxed by this harness. Use synthetic inputs and local fake services; never attach live services or production data to these cases. Endpoint hashes alone cannot prove no temporary mutation occurred.

Native child trees are copied using the existing history reader. Separate CLI trials launched by Build are not native descendants and need their own recorded session IDs; the evaluator must leave missing trial evidence as a gap. Timeout stops the owned local process tree; remote continuation cannot be independently guaranteed. Available model, token and cost records stay in each `native.json`; missing usage is not zero cost.

## Validation, 2026-09-18

Claude Code 2.1.270, configured model/effort settings (observed values were not recorded then), Windows. These observations apply to the recorded package snapshots, not every host or model.

| Pilot | Observed result |
| --- | --- |
| Revised smoke | **4/4 acceptable, all completed and independently audited in 175.5s; peak 3 harness sessions.** Composition exercised nested procedures, independent invoice review, a separate public-summary maker and scoped guidance. |
| Evaluator calibration | **4/4 matched:** accepted baseline/verbosity, rejected skipped review, marked missing evidence inconclusive. |
| Build → fresh reuse | Authoring timed out at 360.8s. Generated workflow and standalone component then completed in 148.2s and 55.1s on unseen inputs; all 10 artifact checks passed. Journey audit timed out; **full authoring contract remains inconclusive**. |
| Example cases | Both reached fresh reviewer dispatch but timed out at 120s before deliverables. Audits preserved partial evidence; **neither example is a behavioral pass**. |

The successful smoke is one sample, not a reliability estimate. Its observed duration was about three minutes within a five-minute cap. Keep full authoring and larger examples opt-in: their tested budgets yielded partial evidence without establishing reliable completion. Build's complete trial-before-review sequence needs a completed run with its inner trial identities captured. Those September 18 trials did not test Codex. The subsequent [Codex gate pilot](gate-results.md) records its own conditions, failures and evidence.

Offline regression tests run without a model:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p "test_e2e*.py" -v
```

On September 20 the latest full offline suite ran 211 tests in 38.2s after the [structure review](structure-review.md): 210 passed, one platform skip. They cover discovery without registry changes, frozen inputs/drivers, parallel dependent stages, bounded sessions, cancellation with complete attempt accounting, partial outputs, objective versus evaluator judgments, changed-evidence rejection, Codex launch/discovery controls, calibration fixtures and the next-stage scorer/policy controls. Local fake agents test the harness, not LLM ability. Existing [upgrade tests](../test_upgrade_e2e.py) still exercise real installation/upgrade from pinned main `16d2644ba25562d66af5648a7dfed8ebde1cfe90`; unavailable Git history is a skip, not a pass.
