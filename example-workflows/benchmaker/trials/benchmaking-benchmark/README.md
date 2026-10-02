# The benchmarking benchmark

Benchmaker delivers benchmarks, and a benchmark is executable, so it can be measured. This folder is the measuring tool: it gives a builder a request, collects the benchmark it delivers, runs that benchmark against pools of subject variants whose order is known, and reports how well the benchmark recovered the order, caught planted defects, resisted cheaters and told the truth about itself. The same request goes to two arms, a builder using Benchmaker and a plain agent with the same tools, so the two deliveries can be compared.

It is code, not a scenario to run by hand. It has no `case.json` and the automated E2E runner does not discover it; its offline unit tests run with the core suite (`python -m unittest discover -s tests` from the repository root). It sits under `trials/`, so installation does not copy it into a home. Run it from this folder.

**Status.** Built and exercised offline, with three live probe calls. No live builder comparison has run: Benchmaker against a plain agent is the next step, and until it runs this folder supports no claim about whether Benchmaker builds better benchmarks. [Results so far](#results-so-far) lists exactly what was run.

## The three meta-tasks

Each meta-task is a request a team might plausibly make, with the public material a builder gets. Everything is in `meta-tasks/<name>/`: `request.md`, the public `interface.md`, `material.json` (sources, licence, attribution, the public sample), `dev-pool.json` and, where the request supplies a subject, `subject/`.

| Meta-task | What the builder is asked for | Real material | How the meta-verifier knows the right answer |
| --- | --- | --- | --- |
| `schedule-nosolver` | A benchmark of how well Haiku 4.5 and Sonnet 5.5 at low effort schedule meetings across several calendars. No solver exists, so the builder must name a representative that stands in for one | [Natural Plan](https://github.com/google-deepmind/natural-plan) calendar scheduling, 1000 records, 40 public (code Apache-2.0, data CC BY 4.0) | An exact oracle that enumerates every valid slot from the interface's semantics, independent of any label. The oracle labels all 1000 Natural Plan golden plans valid |
| `logtriage-llm` | A benchmark to compare versions of a CI-failure triage prompt. The solver is supplied: one Haiku 4.5 low call per build log that returns the failing lines | [LogChunks](https://zenodo.org/records/3632351), 797 real Travis CI logs with human-labelled failure chunks, 60 public (CC BY 4.0) | The labelled chunk. A delivered log, which may be an excerpt, is mapped back onto the labelled log by its lines |
| `calendar-skill` | A suite that answers whether the `booking-rules` skill makes a calendar-editing agent better, at matched model, tools and budget | The scheduling material, 20 public records, plus a written team booking policy | The correct booking applied to the calendar files, with a check that every existing entry survives |

The subjects are real: `logtriage-llm/subject/agent` makes one `claude -p --safe-mode --tools ""` call per log, and `calendar-skill/subject/agent` runs a Claude session with Read, Write, Edit, Bash, Glob and Grep, with or without the skill's plugin directory. The skill's helper script is partial on purpose. It handles busy time, work hours, the grid and buffers, but not room features or focus-block exceptions, so an agent still has to reason and the with-skill arm does not sit at the ceiling.

Licence checks and attribution are recorded in each `material.json`. Both datasets have limits the card has to report. Natural Plan is generated from templates, not logged requests, and has no rooms, buffers or mixed time zones. LogChunks has been public since 2020, so compared models may have seen it.

The request budgets are filled from a profile when a build starts. `small` allows 60 solver runs of 2 minutes at concurrency 8 and a 60-minute builder wall cap; `standard` allows 120 runs, 2 minutes, concurrency 8 and 90 minutes. `logtriage-llm` allows 150 runs at `standard`, and `calendar-skill` uses 5-minute runs at concurrency 6.

## What the meta-verifier runs and measures

`verify` takes a delivered `benchmark-run/` and never reads its claims as evidence. It keeps a pristine copy of the delivery, flags files that are byte-identical to the committed reference packages, and runs preflight once. It then runs the package's own `python run.py full --agent <member> --output <dir>` once for each pool member, plus the package's `@reference` and `@noop`, each in a fresh copy of the package with a minimal environment and a cap on wall time. Each member is a small agent directory whose shim records every invocation, so the meta-verifier has its own account of what ran.

**Gates come first.**

| Gate | Passes when |
| --- | --- |
| G1 executability | Preflight exits 0, every member run completes with schema-valid records, and at most 5% of planned units were lost to infrastructure errors |
| G2 reference and floor | The reference solves every task, the no-op earns no full success, and its mean credit is at most 0.1 |
| Crosscheck | The invocation log agrees with `attempts.jsonl` and the summary counts, and regrading every captured final workspace through the package's `grade` command reproduces the package's own grades |
| Staging | No cheater member reached answers or evaluator files from the solver's workspace |

A failed gate is reported, not averaged away, and the metrics below it are marked unreliable.

**Then the metrics.** A metric that cannot be computed is reported as not computed, never as zero, and there is no composite score.

| Metric | What it asks |
| --- | --- |
| M1 cheaters | Does any task pay a floor or a cheater? A task is hackable when one earns full success on it or at least half of the oracle's credit |
| M2 order recovery | How many of the known pairs does the benchmark order correctly? Pair accuracy with a 90% interval, tau-b, and the probability of that accuracy by chance, which is exact for small pools and Monte Carlo above nine members |
| M3 defect kills | Does each killable planted defect score significantly below the oracle (one-sided sign-flip test, p < 0.05)? A defect the checker never judged wrong on this package is excluded as equivalent, and a package with fewer than five tasks cannot resolve a kill at all |
| M4 contrasts and noise | Do the designated must-resolve contrasts separate? Do A/A pairs, two copies of one member, falsely separate? |
| M5 reliability | Test-retest agreement and noise, computed only where members have repeated full runs |
| M6 verifier accuracy | Submissions the meta-verifier builds from its own oracle, labeled valid or invalid, go through the package's `grade`: true-positive and true-negative rates, with every false accept and reject listed |
| M7 task profile | Tasks the reference fails, tasks that give a floor credit, flat tasks where every attempting member ties, and inverted tasks where a known-stronger member scores lower |
| M8 range | Which LLM members score strictly between 0 and 1, so neither floor nor ceiling hides a difference |
| M9 claim calibration | Do the typed claims in the package's `card.json` match what was measured? Which are contradicted, which understate, and did the card disclose the gaps measured? |
| Speed | Wall time per member, and the overlap achieved against the overlap declared |

`report.md` lists the gates first, then one row per metric, then contradicted claims and measured gaps. `report.json` has the same content. The scoring constants are echoed into the report's conditions.

## The pools

A pool is a set of anonymous agent directories plus a private `ORDER.json` that says what each one is and which orders are known. Scripted members cost nothing and fall into these groups.

- **Oracle** and **oracle plus one realistic defect**. The defects are the domain's, such as ignoring a participant, skipping the constraints list, a boundary off by one granule, ignoring time-zone offsets and always or never declaring a request infeasible for scheduling; a shifted range for log triage; and ignoring a policy rule, clobbering existing entries, double-booking a room or claiming a booking without making it for calendars.
- **Natural heuristics**, such as the first common free slot or the last 50 lines of a log.
- **Ladders.** The oracle with a killable defect applied with probability q per attempt, at three values of q. The rungs have a known order by construction, and a second copy of the middle rung gives a free A/A pair.
- **Floors**: no-op, empty output and echoing the input.
- **Cheaters**: reading answer-like files in the workspace, walking its ancestors for evaluator-looking names, overwriting verifiers and writing grade files, exiting with a success message, and copying an example output from the prompt.
- **LLM members**, only with `--llm`, using Haiku 4.5 and Sonnet 5.5 at low effort: the plain subject, a stronger model, a weaker variant such as truncated input or un-numbered log lines, and for calendars the skill loaded, hidden or inverted. Their order is a hypothesis until the private reference slice confirms it.

The committed `dev-pool.json` files hold small pools of the scripted kinds with explicit names. The held-out pools are generated into the private store with anonymous random ids.

## Public and private

The repository is public and builders have web access, so anything committed here may be known to a builder.

| In the repository, public | In the private store, held out |
| --- | --- |
| Requests, interfaces, material descriptions and the public sample of each dataset | The rest of each dataset: 960 of 1000 scheduling records, 737 of 797 logs |
| Subject agents and the `booking-rules` skill | Held-out pools, with anonymous member ids and their `ORDER.json` |
| Domain code, member behaviours and the scoring code | Private defect and cheater operators, which are never committed |
| Development pools (`dev-pool.json`, labelled exposed) and offline reference packages | The private reference slice and each pool's confirmations |

Results against a development pool support development claims only. The held-out pools stay out of the repository, but their behaviours are drawn from public domain code, so the split protects the pool's composition and order, not the idea of the test.

The store defaults to `~/.bmk-eval/meta` and `METABENCH_STORE` or `--store` overrides it. Package runs write under `--out-root` (default `~/bmk-meta-out`) and builds work under `--work-root` (default `~/bmk-meta-work`). The commands refuse a store inside the repository, the output root or the work root. The store is a local directory; nothing backs it up.

```text
<store>/material/<meta-task>/{source/, public/, held-out/, split.json}
<store>/pools/<meta-task>/<pool-id>/{ORDER.json, members/<anon>/}
<store>/private_members/*.py            held-out defect and cheater operators
<store>/slices/<meta-task>/<slice-id>/package/
<store>/runs/<run-id>/{report.json, report.md, ...}
```

**Isolation is by convention.** A builder runs as the same operating-system user that owns the store, so a determined one could read it. The tool flags a builder's reads outside its workspace, its package directories and the interpreter locations by scanning the transcript afterward; it does not prevent them. A fabricated result is stopped by other controls: the crosscheck and the regrade of captured workspaces, and the fact that the meta-verifier runs the delivery itself. Real isolation needs a separate account or machine, which this folder does not set up.

## Commands

Run from this folder. Everything is `python -m metabench <command>`, with `--store`, `--out-root` and `--work-root` available on each. Exit codes: 0 done (for `verify`, every gate passed), 1 a gate failed or a check did not pass, 2 refused or a bad argument.

Offline, no model calls:

```sh
python -m unittest discover -s tests
python -m metabench refpkg assemble schedule-nosolver --out <dir>
python <dir>/run.py preflight
python public/conform.py <dir>
python -m metabench pool generate --meta-task schedule-nosolver --dev
python -m metabench verify --meta-task schedule-nosolver --package <dir> --pool <pool-id> --jobs 8
python -m metabench build --arm benchmaker --meta-task schedule-nosolver --model claude-sonnet-5-5 --effort low --budget small --plan
python -m metabench selfcheck --meta-task schedule-nosolver --full
```

`refpkg assemble` builds the hand-made reference package from committed synthetic instances (`--instances offline`, the default), from fetched public material or from a directory of instances, and copies the kit in. `public/conform.py` is the standalone shape check builders receive. `build --plan` prints both arms' commands, the workspace listing and the budget and launches nothing. `selfcheck` runs the mutation self-validation described under [Results so far](#results-so-far).

Generating a private pool needs network once, for the real material, and no model:

```sh
python -m metabench material fetch --meta-task schedule-nosolver
python -m metabench pool generate --meta-task schedule-nosolver
python -m metabench slice build --meta-task schedule-nosolver
python -m metabench confirm --meta-task schedule-nosolver --pool <pool-id> --slice <slice-id>
```

`material fetch` downloads the dataset into the store and splits it into public and held-out parts. `pool generate` writes a pool with anonymous ids and its `ORDER.json`. `slice build` generates a private package from held-out material, the reference slice. `confirm` runs the pool on the slice with the meta-checker and writes `confirmations.json`; with `--llm` it also runs the LLM members, which costs money, and promotes an LLM pair to a known pair only when the slice resolves it in the expected direction.

Paid runs, which are subscription usage:

```sh
python -m metabench build --arm benchmaker --meta-task schedule-nosolver --model claude-sonnet-5-5 --effort low --budget small
python -m metabench build --arm plain --meta-task schedule-nosolver --model claude-sonnet-5-5 --effort low --budget small
python -m metabench verify --meta-task schedule-nosolver --package <delivered benchmark-run> --pool <pool-id> --arm benchmaker --build <build-id> [--llm]
python -m metabench report --runs <run-id> <run-id>
```

A build records its session, so `--resume <session>` continues one that stopped at a usage limit, and the wall cap spans resumes. `report` prints one comparison table over any number of meta-verification runs. One build per arm is descriptive only, so a comparison of arms needs repeated builds.

## Results so far

Nothing here is a live comparison of builders.

- **Offline tests.** Unit tests cover the domains, pools, members, shim, crosscheck, measurement, claims, report, builders and transcript scanning, all without model calls or network. They run with the core suite.
- **Zero-model-call verification.** The meta-verifier was run on the `schedule-nosolver` reference package against its development pool. Every gate passed, the verifier accepted every labeled valid submission and rejected every labeled invalid one, and the planted defect was killed. This shows the harness agrees with itself. It says nothing about builders. TODO(coordinator): refresh this paragraph from the final integration run.
- **Mutation self-validation.** Each reference package is deliberately broken (for example a verifier that accepts empty output, answers reachable from the workspace, a runner that reports counts it did not run, or a vacuous card) and the meta-verifier must catch it while passing the unmutated package. See the self-validation report. TODO(coordinator): state the kill matrix and the zero-model-call confirmation.
- **Live probes.** On Claude Code 2.1.284, three single runs of the supplied subjects worked and their output graded correctly.

| Probe | Result |
| --- | --- |
| Triage subject, Haiku 4.5 low, one call | Completed in 9.0 s for $0.014; the answer came in a code fence and parsed to the exact failure chunk |
| Triage subject, Sonnet 5.5 low, one call | Completed in 4.3 s for $0.017; same chunk |
| Calendar subject, Haiku 4.5 low with the skill loaded | Completed in 216 s over 18 turns for $0.114; the skill was invoked once. It booked a valid but suboptimal slot (14:15 against the oracle's 11:45), which the domain checker graded correctly. Haiku agent runs are slow, so calendar pools are the expensive ones |

**Not covered yet.**

- The live comparison of Benchmaker against a plain agent, and the paid LLM members' confirmation on the reference slice.
- Workflow against a single agent: native multi-agent sessions per attempt cost too much at current usage to include in the first version.
- An environment-heavy domain. Trial 4 showed pandas work rewritten without pandas, and these meta-tasks test that only indirectly. The candidate is repairing code from DS-1000 (CC BY-SA 4.0) in a `uv` environment.
- A Codex builder arm, and the SQL and extraction domains, whose licences need checking.
- POSIX for `metabench`. It has been run only on Windows. The kit's own tests have also passed under Ubuntu on WSL.

The fourth known-ordering trial, which motivated this tool, is described in [DESIGN](../../DESIGN.md).
