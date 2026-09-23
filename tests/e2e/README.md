# Behavioral E2E tests

Run ordinary requests through a native agent, preserve the execution, then have a fresh evaluator review outcomes and process. Different valid plans and harmless verbosity pass; unsupported review, unauthorized effects and material wrong results do not. An unfinished run is inconclusive.

```powershell
python tests/e2e/run.py --list
python tests/e2e/run.py --host codex --plan                              # smoke by default; launches nothing
python tests/e2e/run.py --host codex --case core/routing --output ../e2e-check   # one trivial attempt, a few minutes
python tests/e2e/run.py --host codex --output ../e2e-codex-smoke         # smoke: 4 attempts at once, 5-10 minutes
python tests/e2e/run.py --host claude --output ../e2e-claude-smoke
python tests/e2e/run.py --suite authoring --output ../e2e-build
```

Python 3.11+ is required. Native runs are opt-in and consume normal agent usage. Use an authenticated Claude Code or Codex CLI; `--host claude|codex` and `--executable PATH` select the host and executable; trials run on cheap models by default (Claude `claude-sonnet-5` at `high`; Codex `gpt-5.6-luna` at `medium`, which completed the suite within its case budgets while `xhigh` exceeded them), and `--model`/`--effort` override that for every session. Configured model/effort settings pass through unchanged, but the host decides what applies; evidence records the observed model and effort. Native controls need validation on the selected host/version; unsupported hosts never substitute another host. Check `--plan` before a long run: it prints the model, effort, jobs, attempts and deadline.

Opt-in development suites: `gates` and `gates-authoring` diagnose work-unit boundaries and Build/Dynamic authoring; `gates-regressions` holds the blocked-authoring prerequisite case and the requested-review calibration source; `next-stage` covers joined multi-guidance review, ordinary research/code and survey requests, a compatible API change, and direct versus saved release briefs. `python -B tests/e2e/next_stage.py --suite next-stage --output ../next-stage-prepared` freezes predictions, cases and runtime packages without model calls; its native execution is explicit and needs `CODEX_API_KEY` or `OPENAI_API_KEY`. These suites have offline scorer controls. Smoke membership is unchanged.

| Selection | Cases |
| --- | --- |
| `smoke` (default) | Trivial Dynamic; explicitly requested review; nested composition with scoped guidance and a fresh maker; required review unavailable |
| `authoring` | Build a personal library, freeze it, then run its larger workflow and reusable component on unseen inputs in parallel |
| `examples` | Shared comparison; Short Video review of a corrupt export |
| Explicit `--case ID` | Selected cases only; repeat the flag to select more |

Repeat `--suite` to combine suites; `--case` adds cases to them.

### Budgets and concurrency

- **Case timeout** (`timeout_seconds`) bounds one attempt's target work, including preparation and stage waits. The smoke and examples cases, `core/research-code`, `core/dynamic-review` and `core/routing` were checked against the 2026-09-22 Codex Luna medium runs and allow at least 1.3 times their slowest observed or estimated completion; other cases have no recent timing. Raise a timeout when a case times out while still making progress.
- **`--audit-seconds`** (default 600) bounds each evaluator. Medium-effort audits took 23-190 seconds; the one xhigh audit took about three times its medium counterparts.
- **Suite deadline.** By default it is derived from the selection: per-attempt budgets (case timeout + audit seconds + 60 seconds of checks, collection and cleanup), summed over `--jobs`, plus the largest budget. A normal run admits every attempt before it. An explicit `--deadline` wins; `--plan` notes when it is below the derived value. Attempts it leaves unadmitted report `Suite deadline before admission` and are counted in the evidence README.
- **`--jobs`** (default 5) bounds concurrent harness sessions, targets and evaluators together. Hosts cap children per session (Claude 20 running subagents; Codex `agents.max_threads`), not sessions per account, so the harness bounds the total. A target plus its children is about four agents: the 2026-09-22 Codex targets never ran more than three children at once, and case requests allow six in all. Audits delegate nothing. Five sessions therefore stay near 20 agents. Build's inner trial sessions are additional. Raise `--jobs` only with account headroom; it shortens wall clock until the longest attempt dominates.
- **`--repeat`** (default 1). Use more only to claim reliability, for example `--repeat 5` on the cases in question. The runner admits the longest cases first, with all their repeats together.

Deadlines bound waiting, not successful completion. Audits start as soon as their own target and checks finish. Dependent stages wait for frozen inputs. Each attempt gets distinct files, homes and native session IDs; there are no automatic retries or cached successes. `schedule.jsonl` logs admission, release, and each session's start and finish.

### Reading results

The evidence README opens with wall-clock seconds, peak sessions and unadmitted attempts, then a row per attempt and a row per case. In `summary.json`, `cases` gives each case's attempts, assessment counts, `all_acceptable` (true only if every attempt passed, pass^k) and observed models. A single attempt is weak evidence either way. For any row that is not acceptable, open `<case>/<attempt>/report.json`: `findings` cite the failed requirement and evidence, `gaps` say what blocked a verdict, such as a stage timeout or an audit that did not finish, `conditions` note what the environment did to the target without changing the verdict (for example, recorded command results showing it could not run Python), and `audit_path` leads to the evaluator's packet and assessment.

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

Case checks read target outputs with `c.json` and harness files (`before.json`, `codex-launch.json`, `evidence/index.json`) with `read_json`, so a missing harness file becomes a gap rather than a target failure. Count new SKILL.md files against `before.json`, which includes Codex's package copies under `.agents/`. Agent facts come from `stages/<stage>/evidence/index.json`: children have `parent_id == root_id` on both hosts, and any other non-root agent was launched by a child; raise when discovery is missing or reports gaps. Preconditions such as the no-review restriction raise when unestablished (inconclusive) rather than failing the target.

## Evidence and assessment

Output must be a new directory outside the checkout. Each case attempt retains frozen scenario files and packages, requests, before/after hashes, native streams, descendant transcripts, artifacts, checks and audits. `summary.json` reports selected, started, completed, audited, not-started and verdict counts; lifecycle counts overlap. `completed` means all target sessions ended successfully, not that their outcomes passed. `audited` means a valid evaluator judgment completed, including an inconclusive judgment. Each `report.json` and summary result carries `observed` models and efforts, tallied from the native records of every target agent; audit packets show each agent's tallies.

Each stage's native evidence records, per delegated child, `launch_context` (`fresh`, `inherited` or `unknown`) with `launch_evidence`: the child's own record and the linked spawn call (Codex v1 `fork_context`, v2 `fork_turns`, Claude `subagent_type`). A child launched with inherited parent history is an invariant violation, so the attempt is a material failure whatever the audit says. An unknown launch, or a spawn call that requested inherited history but cannot be linked to a recorded child, is a gap.

Audits receive indexed excerpts, actual files, selected contracts and private acceptance notes. Excerpts identify truncation and full source locations. Auditors must not repair, execute candidate code or delegate. Claude exposes read tools only; Codex uses a read-only sandbox with shell reads available and native delegation disabled. Required material findings cite evidence and consequences. The aggregator cannot overrule objective failures with evaluator approval. Passing checks without sufficient audit evidence remains inconclusive. No private chain of thought is required or inferred.

Frozen execution hashes are checked before and after auditing. Re-audit appends a new verdict and preserves the current evaluator brief/schema and native settings; it never changes the original report or resumes a target:

```powershell
python tests/e2e/audit.py ../e2e-smoke --jobs 5 --audit-seconds 600 --deadline 1800
python tests/e2e/calibrate.py --source ../e2e-smoke/core/requested-review/1 --output ../e2e-calibration
```

Calibration uses four explicitly labeled evaluator controls: a genuine successful trace, harmless verbosity, skipped required review and missing evidence. Altered controls are not target executions. Use intact sealed requested-review evidence whose baseline is accepted. Recalibrate after material evaluator/model changes; four controls do not establish universal judge accuracy.

Claude loads frozen session-local plugins, disables user-configured plugin activations/hooks, MCP and account-synced claude.ai skills and plugins, and retains authentication and model/effort settings. It records the requested effort sources it finds (`CLAUDE_CODE_EFFORT_LEVEL`, `effortLevel`, `modelSettings`) and reports a gap when the root session's recorded effort differs from the requested value (the host decides which request applies; a top-level user `effortLevel` does not apply to Opus 5.5); an audit keeps its verdict and records such condition gaps as observations; `modelSettings` is recorded but not interpreted. Host built-in skills may remain advertised; inventory is recorded. Codex uses complete package copies under each workspace's `.agents/skills`, checks native discovery, and passes configured model/effort through without changing global registration, reporting a gap when `turn_context` differs; every invocation requests `windows.sandbox = "unelevated"`, since the elevated sandbox could not start the per-user Python in a 2026-09-22 probe on Codex 0.156.0, and `codex-launch.json` records the mode, which native metadata does not show. Its targets request workspace-write; audits request read-only and disable native delegation. Audit shell subprocess delegation is not independently filtered; sandbox enforcement needs a host-specific probe. Use `--executable` when the CLI on PATH is older than the configured model requires; the observed models show which model actually ran.

Targets receive only ordinary inputs, not acceptance/checks or reserved reuse data. This is context separation, not verified filesystem isolation. Targets with shell access and checks that execute generated programs are not security-sandboxed by this harness. Use synthetic inputs and local fake services; never attach live services or production data to these cases. Endpoint hashes alone cannot prove no temporary mutation occurred.

Native child trees are copied using the existing history reader. Separate CLI trials launched by Build are not native descendants and need their own recorded session IDs; the evaluator must leave missing trial evidence as a gap. Timeout stops the owned local process tree; remote continuation cannot be independently guaranteed. Available model, token and cost records stay in each `native.json`; missing usage is not zero cost.

## Current evidence and gaps

- 2026-09-18, Claude Code 2.1.270 on Windows (observed models and efforts were not recorded then): smoke 4/4 acceptable and independently audited in one sample; evaluator calibration matched its four controls. Build's authoring and both example cases timed out, so full authoring and the examples have no behavioral pass.
- Historical, Claude trials recorded before 2026-09-22: automatic selection chose Dynamic for a research-to-code request but skipped it for a trivial file-writing request; explicit invocation worked.
- 2026-09-20, Codex gate pilot: host transport failures, timeouts and the account usage limit interrupted it, and the native Codex calibration did not run. Its native gate cases on Codex 0.154.0-alpha found four acceptable (research to code, missing vendor evidence, mixed-guidance page, review then single repair) and two Build/Dynamic save-and-reuse journeys judged material process failures after inner-trial transport blocks; the next-stage suite has offline scorer controls only.
- 2026-09-22, Claude Code 2.1.280: a baseline of five cases was inconclusive for every attempt because the account had reached its usage limit.
- 2026-09-22, Codex 0.156.0 at `gpt-5.6-luna` medium: two arms of 9 cases × 3 took 25-29 minutes at 3 jobs, with all three slots busy 94% of the time; replaying those durations gives about 15 minutes at 5 jobs. Their timings set the current case and audit budgets.
- Gaps: single attempts are not reliability estimates; Build's trial-before-review sequence needs a completed run that captures its inner trial identities.

Offline regression tests run without a model:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p "test_e2e*.py" -v
```

The offline tests cover discovery without registry changes, frozen inputs/drivers, parallel dependent stages, bounded sessions, cancellation with complete attempt accounting, partial outputs, objective versus evaluator judgments, changed-evidence rejection, the derived suite deadline, the full Claude launch line, Codex launch/discovery controls, calibration fixtures and the next-stage scorer/policy controls. Local fake agents test the harness, not LLM ability. The [upgrade tests](../test_upgrade_e2e.py) exercise real installation and upgrade from a fixed old main commit; unavailable Git history is a skip, not a pass.
