# Benchmark kit interface

The kit gives a benchmark package its runner and record formats: capped process trees, concurrency, a ledger with resume, byte identity, staging, grading, statistics and a self-check. Tasks, environments, verifiers, references, judges and adapters stay each package's own; the kit supplies none. Standard library only, Python 3.11+, Windows and POSIX. Directory names follow Harbor's (`instruction.md`, `environment/`, `solution/`, `tests/`) without a claim of Harbor parity.

## Assemble a package

Copy `scripts/benchkit/` to `<package>/benchkit/` and `scripts/run.py` to `<package>/run.py` (not `__pycache__`), then add the package's own parts. Task dependencies (a `uv` project, a container) are the package's own files, provisioned by `suite.json` `provision` commands.

```text
<package>/  README.md  card.json  suite.json  run.py  benchkit/  tasks/<id>/  admission/<id>/  adapters/<name>/run_agent.py  research/  rejections.jsonl
```

## Solver protocol

An agent is a directory holding `run_agent.py`, run as `python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS`, cwd the workspace.
- The workspace holds the task's `environment/` files. The workspace, the prompt file (`instruction.md`), the transcript path and the files the agent's stdout and stderr land in are all in a temporary root outside the package and the output directory (`<root>/workspace/` and `<root>/solver/`); no path the agent is handed, or can learn from its own open files, leads into the output directory. Deliverables are the workspace's final state, as the instruction names them. The agent may write the transcript file.
- Enforced: those paths, the staging refusals below, and that the kit grades a copy of what it captured. Conventional: the agent is an ordinary process of the same user and the kit does not sandbox it; the adapter's own directory lives in the package, so an adapter that gives a model tools must confine them and not expose that directory's parents. Isolating a hostile solver is the host's job.
- Its last stdout line is `{"status": "completed", "exit_code": 0, "seconds": 7.9, "model": "claude-haiku-4-5", "cost_usd": 0.018, "final": "text"}`. `status` is completed, refused, cut-off, timeout, usage-limit or error; `model` and `cost_usd` may be null; extra keys are allowed.
- Exit codes: 0 completed, refused or cut-off; 2 timeout; 3 usage-limit; 1 other. A line that disagrees with the exit code is an infrastructure error.
- The kit stops the whole process tree at `--timeout` plus `grace_seconds` (default 5), so an agent needs no timer of its own. Windows: a kill-on-close job object holds every descendant. POSIX: the agent leads a process group and the group is killed; a descendant that starts its own session (`setsid`) escapes the group, survives, and is not reported as `left_running`. That is a known limit of the standard-library approach.
- Built-ins: `@reference` runs `tasks/<id>/solution/solve.py --workspace DIR`; `@noop` does nothing.

| Solver outcome | Execution status |
| --- | --- |
| completed, refused, cut-off | same name |
| timeout, or the kit's cap | agent-budget-exhausted |
| usage-limit | interrupted: admission stops, the run exits 4, `resume` relaunches the unit |
| error, no line, crash, contradiction | infrastructure-error, retried within `transient_retry_budget` |
| deadline or Ctrl-C while running | canceled |

The first four statuses are graded; the rest stay unscored. `left_running` marks an attempt whose solver left processes alive after exiting; the kit stopped them.

## Tasks

```text
tasks/<id>/  instruction.md  task.toml  environment/  solution/solve.py  tests/verify.py
```

`environment/` is public and may be absent. Both scripts run with the runner's Python. `solution/solve.py --workspace DIR` computes the deliverable in DIR. `tests/verify.py --task TASKDIR --workspace COPY --result FILE` (cwd the task dir) grades a scratch copy of the captured final workspace after the solver tree is gone, and writes FILE.

```toml task.toml
[metadata]
family = "arithmetic"
source_group = "g1"
split = "development"       # or "held-out"
anchor = false
smoke = true                # in the smoke profile; quick = true joins the quick profile
quick = true
weight = 0.5                # optional: all tasks or none; sum 1, renormalized over the tasks a run selects
difficulty = "why it is hard"
expert_minutes = 5
time_estimate = "author"    # or "measured"

[agent]
timeout_sec = 60

[verifier]               # optional
timeout_sec = 30         # default 60
```

Staging refuses, and the run exits 2: an evaluator name (`solution`, `tests`, `labeled`, `admission`, `evaluation`, `identity`) in any path under `environment/`, a link, or a non-empty staged file byte-identical to a file under `solution/` or `tests/`.

```json verifier
{"grading_status": "scored", "full_success": false, "credit": 0.75,
 "dimensions": {"valid": {"credit": 1.0, "weight": 0.5, "required": true}, "optimal": {"credit": 0.5, "weight": 0.5, "required": true}},
 "critical_failures": [], "reason": ""}
```

`grading_status` is `scored` or `indeterminate` (with a reason); `credit` is the weight-sum of the dimensions in [0, 1], or null when a required dimension is unjudged, which leaves bounds. A nonzero exit, a missing or malformed result, a timeout or a contract violation (a critical failure with `full_success` true, weights not summing to 1, credit outside [0, 1]) leaves the attempt `unscored` or `indeterminate` with the reason.

## suite.json

```json suite.json
{"name": "schedule-dev", "repeats": 3, "concurrency": 8, "deadline_seconds": 3600, "grace_seconds": 5,
 "attempt_seconds_estimate": 8, "attempt_cost_estimate_usd": 0.02, "transient_retry_budget": 0, "launch_budget": 120,
 "provision": [["uv", "sync", "--project", "environments/py"]], "observe": [["python", "--version"], ["uv", "--version"]],
 "metrics": {"primary": "full_success_rate"}}
```

`name`, `repeats`, `concurrency` are required. `launch_budget` counts every launch over the whole run, retries and relaunched interrupted attempts included; none declared means unbounded. `provision` commands run once, in `preflight`, cwd the package. `observe` commands run at the start of each run; their output lands in `run.json` and `resume` refuses when it differs. Nothing is pinned or hashed.

## Commands

`python run.py <command>`; D is an agent directory (from the cwd or the package), `@reference` or `@noop`:

| Command | Effect |
| --- | --- |
| `preflight [--agent D] [--profile P] [--split S] [--report F]` | Validates layout, `task.toml`, `suite.json`, card claims and staging; provisions; records `observe`; runs the selfcheck; prints planned attempts, caps, estimated and worst-case wall time and estimated spend. No model calls |
| `smoke\|quick\|full --agent D --output O [--repeats K] [--jobs N] [--deadline S] [--tasks A,B] [--split S] [--stop-band LOW HIGH [--level L]]` | Runs the profile into a new O. Smoke and quick use tasks flagged so, one repeat each; full uses all tasks and `repeats`. `--tasks` replaces the selection; `--split development\|held-out` keeps only that split's tasks. A selection that matches no task is refused |
| `resume --output O [--jobs N] [--deadline S]` | Continues O from its ledger after comparing retained bytes and observed versions |
| `rescore --output O` | Grades captured workspaces again with the current verifiers into `grades-<n>.jsonl` and refreshes the summary; nothing relaunches |
| `grade --input I --output F [--jobs N]` | Grade-only: `I/<task-id>/<submission-id>/` are final workspaces; writes one JSONL row per submission with `task`, `submission`, the verifier fields, `reason`, `seconds` |
| `compare --a O1 --b O2 [--metric full_success_rate\|mean_credit] [--split S] [--output F]` | Paired per-task differences with cluster intervals (`benchkit.aggregate.paired`); tasks of several splits are paired together only with a warning, `--split` takes one |

Exit codes: 0 every planned unit is terminal; 1 harness error, including a failed selfcheck; 2 refused (changed bytes or observed versions, a held `OWNER`, a staging leak, an invalid suite or card, a selection that matches no task, a bad argument); 3 stopped by the deadline or launch budget with units not launched; 4 interrupted (usage limit or Ctrl-C), resumable. A stale `OWNER` after a hard kill is removed by hand.

## Run directory

```text
O/  run.json  identity/  OWNER  ledger.jsonl  attempts.jsonl  summary.json  attempts/<task>/<repeat>-<retry>/  grades-<n>.jsonl  summary-<n>.json  rescore-<n>/
```

- `identity/` is a read-only copy of `suite.json`, `tasks/`, `adapters/`, `run.py`, `benchkit/` and the agent directory; `resume` compares bytes.
- `ledger.jsonl` is append-only: `planned`, `launched` (before dispatch), `graded`, `finished`, `note`. It is the only record of what ran; `attempts.jsonl` and `summary.json` are rebuilt from it.
- An attempt folder holds `prompt.md` (copied from the task), `workspace/` (the captured final copy), `transcript.jsonl` if written, `solver.json` (command and live workspace path, which name the temporary root, `capture_skipped` and the outcome), `stdout.txt` and `stderr.txt` (all three moved in once the solver's tree is gone; a link the solver left in their place is dropped), `grade.json` and the verifier's own files.
- Capture never drops an attempt: an entry the solver left that cannot be copied (a pipe or socket, an unreadable file or folder, a name the host refuses) is skipped and listed in `capture_skipped` (up to 50 `path: reason` lines, then a count), and the workspace is graded as captured, so a missing deliverable is a scored failure. Only a fault of the host (no destination, a full disk, exhausted handles) is an `infrastructure-error`. Links are never copied. Windows long paths are handled.
- The workspace is copied twice per graded attempt (the capture, then a scratch copy for the verifier) and once more per `rescore`; a task with a heavy environment pays that in attempt time.
- `rescore` keeps the replaced summary as `summary-<n-1>.json`; `summary-<n>.json` is the result of `grades-<n>.jsonl`; `rescore-<n>/` holds the new verifier files.
- A unit is one task repeat; its final attempt (highest retry) decides it. A repeat the stop band skips is `not-launched` with a reason beginning `stopped early`, listed in `exclusions`.

```json attempt
{"task": "t01", "repeat": 1, "retry": 0, "status": "completed", "reason": "", "started": "2026-10-02T10:00:00Z", "finished": "2026-10-02T10:00:08Z",
 "seconds": 7.9, "exit_code": 0, "model": "claude-haiku-4-5", "cost_usd": 0.018, "left_running": false,
 "grading_status": "scored", "full_success": false, "credit": 0.5, "dimensions": {}, "critical_failures": [], "grade_reason": "",
 "workspace": "attempts/t01/1-0/workspace", "transcript": "attempts/t01/1-0/transcript.jsonl", "capture_skipped": []}
```

`summary.json`: splits are never pooled. `splits` gives each split's rollup (`development`, `held-out`; a task without one is `unspecified`), and `overall` and `families` cover only the headline split, named in `overall.split`: held-out when the run has held-out tasks, else development. A run of one split reports that split, and the printed headline of a mixed run lists the splits apart. `overall`, each `splits` entry and each `families` entry exclude anchors and give `full_success_rate`, `mean_credit` (null when a required dimension is unjudged), `credit_bounds`, `critical_failures`, `scored_tasks`, `missing_repeats`, `anchors_excluded`. Execution time sums solver seconds and grading time sums verifier seconds over attempts; setup and total are wall time.

```json summary
{"suite": {"name": "schedule-dev", "tasks": 1},
 "run": {"profile": "full", "agent": "@reference", "repeats": 2, "jobs": 2, "started": "2026-10-02T10:00:00Z", "finished": "2026-10-02T10:00:09Z",
         "wall_seconds": 9.0, "attempt_seconds_sum": 14.0, "achieved_overlap": 1.56, "peak_concurrency": 2, "deadline_reached": false,
         "observed_versions": {"python --version": "Python 3.14.6"}},
 "counts": {"planned": 2, "launched": 2, "completed": 2, "scored": 2, "passed": 1, "failed": 1, "unscored": 0, "canceled": 0, "not_launched": 0, "retries": 0,
            "by_status": {"completed": 2, "refused": 0, "cut-off": 0, "agent-budget-exhausted": 0, "infrastructure-error": 0, "canceled": 0, "interrupted": 0, "not-launched": 0}},
 "overall": {"full_success_rate": 0.5, "mean_credit": 0.75, "credit_bounds": [0.75, 0.75], "critical_failures": 0, "scored_tasks": 1, "missing_repeats": 0, "anchors_excluded": 0, "split": "development"},
 "families": {"scheduling": {"full_success_rate": 0.5, "mean_credit": 0.75, "credit_bounds": [0.75, 0.75], "critical_failures": 0, "scored_tasks": 1, "missing_repeats": 0, "anchors_excluded": 0}},
 "splits": {"development": {"full_success_rate": 0.5, "mean_credit": 0.75, "credit_bounds": [0.75, 0.75], "critical_failures": 0, "scored_tasks": 1, "missing_repeats": 0, "anchors_excluded": 0}},
 "tasks": {"t01": {"family": "scheduling", "split": "development", "source_group": "g1", "anchor": false, "planned": 2, "scored": 2, "full_success_rate": 0.5, "mean_credit": 0.75,
                   "critical_failures": 0, "statuses": {"completed": 2}}},
 "cost": {"usd_known": 0.04, "attempts_with_unknown_cost": 0},
 "time": {"setup_seconds": 0.4, "execution_seconds": 14.0, "grading_seconds": 0.6, "total_seconds": 9.0}, "exclusions": []}
```

## Sequential stopping

`from benchkit.stopping import decide` (stdlib, no run needed): `decide(successes, attempts, low=0.2, high=0.8, max_attempts=8)` (`low`, `high` and `max_attempts` are required keyword arguments; `level` defaults to 0.9) returns `below` or `above` when the exact Clopper-Pearson interval at `level` lies wholly outside the target band, `inside` when wholly within it, `exhausted` at `max_attempts` otherwise, else `continue`. During calibration (`full --tasks <id> --repeats N --agent D --output O` runs one candidate), call it after each scored repeat of a task and stop that task on any result but `continue`; stopping on a decisive result is sequential, so use a higher `level` where a wrong stop is costly. `--stop-band LOW HIGH` does this per task inside a run on full success, between repeat rounds, and records the skipped repeats. Calibration attempts are never measurement.

## Typed claims

`card.json` holds `conditions` (named systems, each with an `agent`: an adapter path or built-in, plus free keys such as `model`, `effort`, `tools`) and `claims`, each citing only named systems:

```json card
{"conditions": {"subject": {"agent": "adapters/haiku-low", "model": "claude-haiku-4-5", "effort": "low", "tools": ""},
                "sonnet-low": {"agent": "adapters/sonnet-low"}, "reference": {"agent": "@reference"}, "noop": {"agent": "@noop"}},
 "claims": [
  {"id": "c1", "type": "interval", "metric": "full_success_rate", "system": "subject", "low": 0.2, "high": 0.45, "level": 0.9},
  {"id": "c2", "type": "order", "higher": "sonnet-low", "lower": "subject", "metric": "mean_credit", "resolved": true},
  {"id": "c3", "type": "rate", "metric": "trivial_credit", "max": 0.0},
  {"id": "c4", "type": "rate", "metric": "reference_pass_rate", "min": 1.0},
  {"id": "c5", "type": "noise", "metric": "full_success_rate", "system": "subject", "sd_max": 0.08},
  {"id": "c6", "type": "target", "system": "subject", "metric": "full_success_rate", "low": 0.2, "high": 0.8},
  {"id": "c7", "type": "cost", "system": "subject", "profile": "full", "usd_max": 3.0, "wall_seconds_max": 900},
  {"id": "c8", "type": "verdict", "supports_claim": false, "reason": "the check ranked against expectation"},
  {"id": "c9", "type": "gap", "category": "unresolved-contrast", "text": "haiku-low vs sonnet-low did not separate"}]}
```

`rate` needs `min` or `max`, `cost` needs `usd_max` or `wall_seconds_max`, intervals have `low <= high` and `0 < level < 1`. `gap` categories: hackable-task, unresolved-contrast, inert-dimension, verifier-false-reject, verifier-false-accept, floor, ceiling, unprotected-boundary, exposure, missing-stage. `preflight` rejects malformed claims.
