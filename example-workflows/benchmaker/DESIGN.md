# Benchmaker: design for a general benchmark authoring workflow

Design report, September 16, 2026. **Status: proposed; implementation and behavioral validation remain to be done.** This report is the requested first deliverable for a new `/benchmaker` in `example-workflows`.

Build a workflow that turns an agent, workflow, or plain-language capability description into a small, runnable benchmark: representative tasks, appropriate environments, defensible grading, and interpretable results. Its default should favor short feedback cycles, bounded asynchronous execution, and ordinary local dependencies. Generality belongs in the authoring process and adapter boundary; each generated benchmark should make a specific, limited claim.

## 1. What the benchmark measures

A benchmark estimates how well a system performs a defined class of work under stated conditions. Unit tests verify particular software behaviors. A benchmark can use tests to grade an agent's delivered program, but passing the runner's tests, inspecting workflow instructions, or exercising isolated helper functions does not measure the workflow's ability to complete user tasks.

For example, a research-workflow benchmark gives the workflow several research assignments, lets it gather evidence and produce reports, then measures the reports' factual support, coverage, and usefulness alongside elapsed time and cost. Checking whether its prompt contains “cite sources” measures something else.

The evaluated system includes its actual model, instructions, tools, memory, orchestration, and execution limits. A workflow comparison should exercise the real workflow. An API call to the underlying model is only an appropriate substitute when that is the stated object of evaluation.

Three layers must remain distinguishable:

| Layer | Question | Evidence |
| --- | --- | --- |
| Harness checks | Does execution and scoring machinery work? | Offline fixtures, process cleanup, result parsing, resume checks |
| Benchmark validation | Are tasks meaningful and solvable, and do graders distinguish acceptable outcomes? | Reference solutions, valid alternatives, plausible failures, independent inspection |
| Agent measurement | How well does the actual system perform these tasks? | Fresh executions, delivered artifacts or state, scores, traces, resource use |

None substitutes for another. A simulator or canned response can validate plumbing; it cannot establish the measured agent's capability.

## 2. Research and comparable projects

This was a targeted review of primary papers, official project documentation, repository history, and local bench-stack code. It was not an exhaustive literature review or a reproduction of published results. Paper versions below identify the text used; living documentation was inspected on September 16, 2026. Recommendations later in this report are design choices, not experimentally established defaults.

### Findings that determine the design

| Source | Finding or structure | Consequence for benchmaker |
| --- | --- | --- |
| Zhu et al., **Agentic Benchmark Checklist**, August 7, 2025, v5 | Separates task validity from outcome validity. Its audits find shortcuts, incomplete graders, impossible tasks, and reporting gaps in prominent agent benchmarks. | Audit both the task and its grader. A high or low agent score alone establishes neither validity nor difficulty. [Paper](https://arxiv.org/html/2507.02825v5) |
| Kapoor et al., **AI Agents That Matter**, July 1, 2024, v1 | Accuracy-only evaluation can reward unnecessary complexity. Holdouts must match the level of generality being claimed. | Report quality with cost; distinguish model and workflow comparisons; split by meaningful task families, sources, or environments. [Paper](https://arxiv.org/html/2407.01502v1) |
| Yuan et al., **LLM-Powered Benchmark Factory / BenchMaker**, February 2, 2025, v1 | Studies credibility, diversity, difficulty, and benchmark-level effectiveness, robustness, and construction efficiency. Direct generation has weaknesses in answer correctness, diversity, and difficulty control. Its main experiments use multiple-choice tasks. | Generate, verify, deduplicate, and pilot. Borrow the generator-quality questions; do not make multiple-choice questions the interface for agents performing real work. The similarly named project is separate from this workflow. [Paper](https://arxiv.org/html/2502.01683v1), [code](https://github.com/ypw0102/BenchMaker) |
| Liang et al., **HELM** | Organizes evaluation by scenarios and multiple metrics, making coverage and tradeoffs explicit. | Build a capability/coverage map and report slices; avoid a universal score mixing unrelated domains. [Paper](https://arxiv.org/abs/2211.09110), [project](https://crfm.stanford.edu/helm/) |
| Anthropic, **Demystifying evals for AI agents** | Distinguishes tasks, trials, graders, and outcomes; combines code, model, and human grading. Recommends starting with a modest set of real failures and reading actual transcripts. | Begin with a useful small suite and inspect pilot evidence. Historical failures inform diagnostic coverage, while representative cases support the broader claim. [Engineering article](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
| Maia Polo et al., **tinyBenchmarks**, inspected v2 | Selects informative examples using previous model-response data, including item-response modeling, to estimate larger benchmark scores efficiently. Evaluates distribution shift, including specialized models. | A calibrated subset can save work. A newly invented handful of tasks has no equivalent guarantee. Start with explicit stratification; add learned item selection only after sufficient historical data exists. [Paper](https://arxiv.org/html/2402.14992v2) |
| Zheng et al., **Judging LLM-as-a-Judge**, inspected v4 | Examines position, verbosity, and self-enhancement biases and limitations of model judges. | Use anchored rubrics and a labeled calibration sample. Hide candidate identity, balance pair order, and inspect disagreement; a second model is not automatically an unbiased authority. [Paper](https://arxiv.org/html/2306.05685v4) |
| Dror et al., **The Hitchhiker's Guide to Testing Statistical Significance in NLP**, ACL 2018 | Statistical procedures depend on the metric, data, and experimental assumptions. | Choose uncertainty analysis from the independent observation unit and sampling design. Avoid automatic significance claims from arbitrary score tables. [Paper](https://aclanthology.org/P18-1128/) |

### Structures worth borrowing

| Project | How it organizes evaluation | What transfers, and what does not |
| --- | --- | --- |
| **Inspect AI** | Tasks combine a dataset, solver, and scorer. Async execution has separate limits for model connections, samples, and subprocesses. | Separate task data, candidate execution, and grading; use bounded concurrency. Inspect is an optional backend when already suitable, not a mandatory dependency. [Tasks](https://inspect.aisi.org.uk/tasks.html), [parallelism](https://inspect.aisi.org.uk/parallelism.html) |
| **HAL** | A common harness accepts different agents and benchmarks, records traces and costs, and exposes cost/performance comparisons. Environments have different requirements. | Preserve the agent's implementation and record the whole condition. Adopt its comparison discipline without requiring its VM or benchmark-specific setup. [Project](https://hal.cs.princeton.edu/about), [harness](https://github.com/princeton-pli/hal-harness) |
| **τ-bench** | Domain policy, database and tools, simulated user, and expected outcomes form an interactive task. Repeated trials measure consistency through `pass^k`. | An episode can be the observation unit; simulator identity and state belong to the condition. Final state alone may miss required explanations or correct refusal. [Paper](https://arxiv.org/abs/2406.12045), [implementation](https://github.com/sierra-research/tau-bench) |
| **AppWorld** | Stateful application tasks use database-state evaluation, including checks for collateral changes. | Grade achieved changes and preservation requirements. A compact local state machine or SQLite fixture can reproduce a relevant subset; it does not automatically reproduce the full benchmark. [Repository and evaluation](https://github.com/StonyBrookNLP/appworld#-evaluating-the-agent) |
| **TravelPlanner** | Natural-language requests are grounded in reference information and graded against commonsense and hard constraints. | Planning benchmarks can use small frozen resource tables and constraint checks while retaining multiple valid answers. Preserve the distinction between planning with supplied facts and obtaining those facts. [Repository](https://github.com/OSU-NLP-Group/TravelPlanner) |
| **DeepResearch Bench** | RACE assesses reports with task-specific criteria and references; FACT evaluates citation behavior separately. | Distinguish report quality from evidence support. Keep judge identity and reference provenance visible; do not infer factual verification from a good writing score. [Repository](https://github.com/Ayanami0730/deep_research_bench) |
| **Harbor / Terminal-Bench task format** | Separates instructions, task metadata, environment, optional solution, and verifier. | Borrow the task boundary and reference-solution check. An environment definition should be proportional to the task; copying the format does not justify a container requirement. [Task structure](https://docs.harborframework.com/core-concepts/tasks/overview), [verifier](https://docs.harborframework.com/core-concepts/tasks/verifier) |
| **AgentSynth** | Offers generated scenario packs with seeded worlds, outcome checkers, and interfaces for external agents. | A useful comparable authoring approach: couple scenarios to observable outcomes and challenge graders with trivial strategies. Project claims are not independent proof of benchmark quality. [Repository](https://github.com/agentsynth/agentsynth) |

## 3. What the local implementations teach us

The current Orchflows checkout, `acb7390273789d3c0372f9f293ca6e6b42ac9fa0`, has no benchmaker workflow. I inspected its predecessor at `4c17a4bc456418611a577e6de270b44255cbb908` from September 10, 2026, including the entrypoint, construction workflow, benchmark-quality standard, manifest, and qualification contract. These were read as source material, not executed.

The predecessor has valuable requirements: meaningful tasks, separate validity and difficulty, observed native execution, reference and negative controls, explicit missing evidence, and protection against evaluation leakage. However, it requires many predeclared inputs, uses `tickets.py` and multiple private workflows, and carries an extensive admission/calibration protocol. Its 30–50% target pass band is explicitly a prior user preference. It should not become a default for a general-purpose rewrite. [Historical entrypoint](https://github.com/DanMcInerney/orchflows/blob/4c17a4bc456418611a577e6de270b44255cbb908/example-workflows/benchmaker/SKILL.md), [quality standard](https://github.com/DanMcInerney/orchflows/blob/4c17a4bc456418611a577e6de270b44255cbb908/example-workflows/benchmaker/standards/benchmark-quality/STANDARD.md).

The local **bench-stack** checkout was inspected at `5318fe10c4b29ecf1949d5cfc7b80c7dcf6bb893`. Its tracked files were clean; untracked working directories were present. Inspection covered its catalog, contracts, engine structure, and representative adapter/manifest/scoring code. I did not install or execute the upstream suites.

| Observation from local code | Design implication |
| --- | --- |
| The catalog lists 23 plugins, with readiness checks separate from discoverability. The benchmark protocol separates enumeration, realization, trial execution, and score extraction. | A generated package needs a preflight and a small execution/grading boundary. Being listed or importable is not evidence that a benchmark ran. |
| Its scheduler supervises worker processes; it is not simply an async API loop. Per-benchmark concurrency limits address particular shared-state or grading hazards. | Keep long calls and subprocesses off the scheduling path; separate operator resource limits from restrictions needed for valid scores. Do not copy its global concurrency sentinel as a portable default. |
| TravelPlanner's manifest documents a 304.8 MB flights CSV loaded by each scorer, despite no platform requirement. | Measure data size, startup, and memory as well as Docker usage. Minimize frozen fixtures while preserving relevant choices and distractors. |
| The DeepResearch adapter implements RACE only, records judge identity, and documents that 0.5 represents reference parity. | Name the metric's meaning and unsupported dimensions; adapters must preserve upstream scoring semantics. |
| STATE-Bench uses separate participant roles and out-of-process verification. Its adapter documents withholding scores for truncated episodes, which then leave the scored mean. | Preserve role separation, but define our own explicit policy for agent budget exhaustion and missing evidence. Report coverage so selective completion cannot masquerade as quality. |
| The `benchmaker` plugin evaluates a sealed 16-case benchmark-construction suite. | It is historical evidence about constructing benchmarks, not a universal template for tasks or a sufficient acceptance suite for the rewrite. |

Source snapshot: [catalog](https://github.com/DanMcInerney/bench-stack/blob/5318fe10c4b29ecf1949d5cfc7b80c7dcf6bb893/BENCHMARKS.md), [contracts](https://github.com/DanMcInerney/bench-stack/blob/5318fe10c4b29ecf1949d5cfc7b80c7dcf6bb893/src/bench_stack/contracts.py), [TravelPlanner manifest](https://github.com/DanMcInerney/bench-stack/blob/5318fe10c4b29ecf1949d5cfc7b80c7dcf6bb893/src/bench_stack/benchmarks/travel_planner/benchmark.toml), [research adapter](https://github.com/DanMcInerney/bench-stack/blob/5318fe10c4b29ecf1949d5cfc7b80c7dcf6bb893/src/bench_stack/benchmarks/deepresearch_bench/adapter.py), [state adapter](https://github.com/DanMcInerney/bench-stack/blob/5318fe10c4b29ecf1949d5cfc7b80c7dcf6bb893/src/bench_stack/benchmarks/state_bench/adapter.py). These commit links identify locally inspected material; public accessibility was not separately verified.

## 4. Proposed user experience and workflow

Accept a target path, callable, command, endpoint, native workflow, or a description of the capability to measure. Infer ordinary choices from the request and available artifacts. Ask only when an unresolved choice materially changes the benchmark's claim, execution permissions, or budget. A description alone is enough to construct a draft; a real invocation is needed to claim agent measurement.

Example requests:

```text
/benchmaker Build a benchmark for this customer-support agent.
/benchmaker Compare these two research workflows; keep a quick run under five minutes.
/benchmaker Benchmark agents that turn a brief into a slide deck.
/benchmaker Make a benchmark for planning with changing resource constraints.
```

`/benchmaker` is the requested short name. Installation and fully qualified native invocation follow the repository's existing host conventions; writing files does not register the skill.

The authoring flow:

1. **Frame and research.** Identify the intended user decision, task population, actual system boundary, observable outcomes, and resource budget. Inspect target examples and relevant primary benchmark precedents. Record unknowns and proposed assumptions in a compact benchmark card. If research access is unavailable, retain a provisional design and name the gap.
2. **Design.** Map capabilities to task families, choose realistic inputs and environments, define graders and success conditions, choose splits and aggregation, and estimate cost. Fix these choices before comparative measurement. Inspect one representative input in each required modality to establish that it can be delivered and evaluated.
3. **Construct.** Write cases, fixtures, adapters, scoring, reference evidence, and commands. Reuse an existing suitable harness where available; otherwise produce a small standalone runner. The generated package contains what this benchmark needs.
4. **Pilot and calibrate.** Exercise the actual target, or an explicitly identified representative agent when no target exists. Check grader controls, valid alternative outcomes, task solvability, observed difficulty, runtime, and cost. Development cases may change here; preserve revisions and rerun affected checks. Calibration does not mean pushing an agent into a prescribed pass band.
5. **Review and deliver.** Conduct one independent review of the frozen candidate and pilot evidence. Make one bounded repair pass and verify affected behavior. Deliver the benchmark, measured limits, and reproducible commands. Required unresolved defects leave the package a draft or partially validated artifact.

Use the caller context for research, design, and construction. Plan **two fresh children**: one `orch-work` worker to independently exercise the package and audit a sample of task answers from visible inputs, and one `orch-review` reviewer after the pilot. The pilot worker should solve its audit sample before seeing author references. One affected trial rerun after repair may use one additional child; there is no automatic second review or open-ended repair loop. Benchmarked agent executions are additional workload, explicitly counted in the pilot budget. All delegation follows the core primitives and inherited caller model/effort choices.

This composition is a proposal for the new workflow, not a claim that those trials occurred during this design report.

## 5. Cases, coverage, and evidence

Start from real user work: representative requests, observed failures, specifications, or expert examples. When these are sparse, generate plausible scenarios from an explicit capability map and label their synthetic origin. Verify their facts and feasibility. Record source identity, capture date where relevant, transformations, and reuse constraints for imported material.

A family should differ in the work it requires, not merely in names or wording. Vary constraints, ambiguity, information location, tools, state transitions, input complexity, and valid solution strategies as relevant. Include routine work and meaningful challenging cases. Keep deliberately adversarial or stress cases identifiable so their oversampling does not silently redefine typical performance.

For a new bounded benchmark, propose roughly **12–24 cases across the important task families** as an initial authoring budget, adjustable to the domain and caller. This is a development starting point, not statistical sufficiency. A general agent may need many separate domain suites. Do not claim broad capability from this count.

Separate development from held-out evaluation before tuning. Keep related variants, common source documents, and shared scenario templates in the same split when they would leak the intended generalization. If the claim concerns new workflows or domains, hold out workflows or domains. A small suite without a defensible holdout remains useful for development, with that limitation stated.

Freeze membership, weights, scorer version, references, and run conditions for a comparison. Retire or revise tasks when evidence shows wrong answers, ambiguity, leakage, obsolescence, or saturation. Changed definitions require a new benchmark version; do not compare old and new scores as though the instrument stayed fixed.

### Generality without flattening every task into text

| Target | Task and lightweight environment | Outcome evidence |
| --- | --- | --- |
| Research or retrieval | Real question plus a frozen corpus or declared live sources | Supported claims, source coverage, contradictions, useful synthesis |
| Writing, slides, images, or audio | Brief, source assets, audience, and constraints | Actual rendered or played artifact; factual and format checks plus anchored human/model judgments |
| Planning | Request and small resource tables with competing feasible choices | Feasibility, constraint satisfaction, plan quality, adaptation to changes |
| Conversation or business tools | Per-episode state, tools, policy, and a scripted or model-driven user | Correct state, preserved unrelated state, required explanations and interaction quality |
| Coding agent | Small pinned project and a realistic change request | Delivered behavior, appropriate hidden checks, regressions, execution cost |
| Browser or desktop agent | Local app fixture or resettable supported environment | Observable UI and persisted state; screenshots where relevant |
| Long-running or multi-agent workflow | Bounded episode retaining relevant dependencies and handoffs | Delivered result, recovery behavior, accumulated cost, memory policy |

These are examples, not a closed registry. A fast slice of a long-running task measures that slice; it cannot establish multi-day persistence. Offline research measures work on the captured information. Live research includes changing availability and content, which must be recorded.

## 6. Grading and calibration

Choose the least expensive grader that validly measures each criterion. Deterministic checks fit structured answers, constraints, executable behavior, and state. Rubric-based model or human judgment fits qualities that lack reliable executable definitions. Mixed grading is expected.

Score observable results. Exact trajectories, tool names, or implementation choices become requirements only when they are part of the intended capability. Accept multiple correct solutions. For stateful tasks, verify both required changes and relevant preservation. An empty response must not earn credit merely because no state should change when the task also requires an explanation.

Separate mandatory constraints from graded quality. A required correctness failure cannot be offset by attractive presentation. Keep dimension scores and evidence visible even when a task-level success decision is binary. For subjective criteria, define concrete anchors and examples, allow ties or indeterminate judgments, and avoid pretending that aesthetic preferences are universal facts.

Validate the grader with:

- A checked acceptable outcome and, where meaningful, a different acceptable outcome.
- A plausible near miss that violates the intended requirement.
- An inert, empty, or shortcut outcome, with its expected treatment stated for that task.
- A bounded independent audit of references and ambiguous or surprising pilot results.

These are grader controls, not the benchmark's main task distribution. Handcrafted good/bad artifacts can establish that a grader distinguishes those artifacts; real target runs are needed to establish empirical headroom and diagnostic value.

For model judges, retain rubric, prompt, model/version, order, raw judgment, and cited artifact evidence. Calibrate against independently adjudicated examples; report disagreement and observed false accept/reject cases. For pairwise comparisons, anonymize and balance order; check swaps on a calibration sample. Repeated judge calls estimate grader variability separately from agent variability. Unreliable grading leaves the affected metric provisional. A missing judge does not trigger an undisclosed downgrade to string matching.

Keep solver, simulator, grader, and reference roles separate. Do not give the solver answer keys, hidden rubrics, or prior successful outputs. Ordinary task requirements remain visible. A temporary directory or Git worktree prevents accidental state sharing but does not enforce secrecy against an agent with broader filesystem access. Claim protected evaluation only when actual access controls or a separate evaluator establish it; otherwise call it local development evaluation.

## 7. Fast execution and modest dependencies

Prefer this environment order, subject to fidelity and access requirements: immutable files or in-memory state; fresh temporary workspaces and ordinary subprocesses; a small local service or dedicated browser context; an existing supported sandbox; containers or VMs when necessary. Generated code with unrestricted host execution may require a stronger boundary. Docker is an option, not a prerequisite or something to remove when its isolation is essential.

Use installed runtimes first. A new standalone runner should default to Python's standard library and `asyncio`; use project-native tooling when that avoids another runtime. Add dependencies only for actual task needs, such as rendering a document, using a browser, or invoking a provider. Do not require a database server, queue, dashboard, embeddings store, or paid judge for all benchmarks.

The runner should:

- Admit independent cases with a configurable bounded concurrency limit. Use async provider clients and subprocess APIs; move blocking or CPU-heavy work off the event loop.
- Keep sequential actions inside an episode ordered. Parallelize independent episodes, not dependent turns. Reset candidate memory between episodes unless memory carryover is the capability under study.
- Give each attempt separate writable state, outputs, and service ports where needed. Share immutable fixtures. Avoid process-global environment or working-directory mutations during concurrent runs.
- Apply separate limits for providers, judges, and expensive local resources. Serialize only the contested resource when isolation cannot resolve the conflict. Record concurrency and hardware for timing comparisons.
- Bound per-attempt execution, total launch count, overall elapsed time, and measured or estimated spend. Reserve capacity for in-flight work before admission. If exact provider spend cannot be enforced, label the limit an estimate and enforce observable call/token/time limits instead.
- Persist results as they finish through one writer or atomic per-attempt records. Resume completed work only under matching benchmark and condition identities; interrupted attempts remain recorded.
- Retry only declared transient infrastructure failures within a small retry budget. Never rerun a failed answer until it passes. Distinguish retries from independent stochastic repetitions and count both costs.
- Cancel and reap owned subprocess trees on deadlines or interruption, using platform-appropriate mechanisms. Record uncertain completion of remote calls; local cancellation alone does not prove remote work or billing stopped.

Provide three explicit run profiles:

| Profile | Purpose | Proposed starting budget |
| --- | --- | --- |
| Smoke | Verify adapter, inputs, grader, and evidence paths | 1–3 representative cases; seconds for offline controls; no capability claim |
| Quick | Frequent feedback across the important families | A fixed stratified subset, commonly 6–12 cases, one attempt each; aim for 2–5 minutes when the task permits |
| Full | Measure the declared suite with the chosen uncertainty/reliability design | All evaluation cases and predeclared repeats; estimated duration and cost shown before launch |

These are configurable targets, not universal limits. A task that intrinsically needs ten minutes cannot be evaluated faithfully in thirty seconds. Optimize setup, scheduling, data size, and grading first; disclose reduced scope when using a shorter task. Report cold setup separately from warm execution, plus generation and grading time. Do not attribute throughput gains from concurrency to lower individual-task latency.

Cache immutable fixtures and optionally re-score saved outputs under an explicit scorer revision. Do not reuse a candidate's previous answer as a fresh trial. Cross-condition caches that reveal prior answers change the experiment and must be excluded or explicitly studied.

## 8. Minimal execution and result contract

Use a small common boundary rather than imposing one agent framework. An adapter executes a complete case or session and returns observable evidence. CLI, API, native workflow, interactive session, and existing-harness adapters can implement that boundary differently. The adapter must preserve the target's native behavior and record any restrictions.

An async Python implementation can expose `run_case(public_case, context) -> result`. A CLI adapter can construct an argument vector, launch the actual candidate command, and translate its native output into the common result. The candidate itself need not emit benchmaker-specific JSON. Interactive adapters own the turn loop and expose final state plus transcript. If a native host lacks automated execution, provide a documented host-driven route and identify the automation gap; do not replace it with a mock and call it measured.

| Record | Minimum content |
| --- | --- |
| Benchmark | Version, intended claim, task population, case/split inventory, metrics, weights, required constraints, run profiles, dependency and access requirements |
| Public case | Stable ID, task, input/asset references, allowed environment/tools, visible deliverable requirements |
| Evaluator case | Capability family, source/group identity, reference evidence, criterion/scorer bindings, expected controls; kept outside solver inputs |
| Condition | Target revision/content identity, actual model/settings when observable, instructions/workflow, tool and network access, memory/reset behavior, budgets and environment |
| Attempt | Case/condition/repetition/retry IDs, status and reason, artifacts or final state, transcript location, phase timings, available usage and costs |
| Score | Scorer identity, criterion outcomes, task success where defined, evidence, grading status, uncertainty or indeterminate reason |

Version data, graders, and relevant fixtures together. Bind results to an immutable manifest/content digest and condition identity, excluding generated result files from the benchmark digest. Record a clean revision or content hashes plus local changes; do not require a Git repository for every benchmark.

Prefer transparent JSON/JSONL and a Markdown report. Keep the generated package self-contained, with these responsibilities even if a chosen upstream harness uses different filenames:

```text
<benchmark>/
  README.md              purpose, commands, requirements, limits
  benchmark.json         identity inputs, profiles, metrics, splits
  cases.jsonl            evaluator inventory with public input references
  inputs/                prompts, assets, resettable fixtures
  evaluation/            scorers, rubrics, reference evidence, controls
  adapter.py             actual target invocation, when needed
  run.py                 small runner or documented upstream entrypoint
  runs/<run-id>/         attempt records, artifacts, summary
```

Only stage public inputs into the candidate's workspace. The directory layout itself is not an access-control boundary.

## 9. Honest aggregation and comparisons

Keep execution status, grading status, and task success distinct. A completed wrong answer is an agent failure. Exhausting a declared agent budget is also an agent failure when completing within that budget is part of success. Provider outage, broken setup, grader crash, and missing evidence are separately identified unscored results. A deliberate robustness task can grade service-failure handling, but ordinary infrastructure failures must not be relabeled as that task.

For every run show planned, launched, completed, scored, passed/failed, unscored, and canceled counts. Report scored quality alongside coverage and the identities/reasons for exclusions. For bounded metrics, optionally show best/worst bounds across missing cases; do not fill missing scores with invented zeros. Suppress an unqualified ranking when missingness or differing case coverage could change it.

Default to per-family results and one primary metric appropriate to the claim, plus elapsed time, usage, and cost where observable. If combining families, declare weights before observing scores. Average repetitions within each case before averaging cases so extra repetitions do not increase a case's weight. Do not average arbitrary upstream scores into a universal “agent quality” number.

Compare conditions on the same cases, resources, tool availability, and budgets, varying only the intended factor for a causal comparison. Interleave or randomize execution order when provider or live-world drift matters. A whole-system comparison may legitimately change multiple factors; describe it accordingly. Include a simple baseline where it helps interpret the result: direct use of the same model for a workflow comparison, an incumbent, or an appropriate heuristic. An oracle is a feasibility control rather than a realistic competitor.

Report per-case deltas and ties. For independent sampled binary cases, an appropriate binomial interval may be useful. For paired heterogeneous cases, consider paired resampling at the independent case or source-family level, retaining repetitions within their groups. A small purposive suite supports a descriptive finite-suite score; resampling it cannot establish population representativeness. Keep agent-repeat uncertainty separate from task-sampling and judge uncertainty. A handful of observations cannot support precise rankings.

Use first-attempt success for ordinary single-attempt use. `pass@k` means at least one success within k attempts; `pass^k` concerns success across all k attempts. Require actual repeated-trial evidence and state the estimator and assumptions. Do not derive suite reliability by exponentiating a heterogeneous aggregate success rate. Predeclare repetitions and stopping rules; label extra exploration separately from final evaluation.

## 10. Library implementation plan

Use the current [Orchflows architecture](https://github.com/DanMcInerney/orchflows/blob/acb7390273789d3c0372f9f293ca6e6b42ac9fa0/docs/architecture.md) and [authoring guidance](https://github.com/DanMcInerney/orchflows/blob/acb7390273789d3c0372f9f293ca6e6b42ac9fa0/guidance/orchflows.md). Keep coordination in the skill, benchmark quality in library guidance, and shared data/execution contracts in references. Resolve dependencies through normal library context. The new workflow should be written afresh; the older schema and ticket runtime are not dependencies.

```text
example-workflows/benchmaker/
  plugin.json
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  README.md
  DESIGN.md
  guidance/benchmarking.md
  references/library-context.md
  references/benchmark-contract.md
  references/research.md
  skills/benchmaker/SKILL.md
  skills/benchmaker/agents/openai.yaml
  trials/<scenario>/request.md
  trials/<scenario>/expected-behavior.md
```

Keep `SKILL.md` short: request interpretation, research/design/construction flow, pilot/review composition, and delivery conditions. Put the operational contract and compact research lessons in the linked references. Preserve full design history here without making it mandatory reading for every invocation. Apply manual invocation settings for both hosts and declare child counts in the README. Generated benchmarks and trial evidence live in the caller's workspace, outside the installed library.

Initially generate or adapt each benchmark's runner to its needs. Add a shared runner template under the owning skill only after cross-domain trials establish which mechanics are truly repeated. This avoids building a universal evaluation framework before validating the authoring workflow. Any added deterministic helper needs targeted tests; that testing remains separate from benchmark validation.

Bench-stack and Inspect integrations are optional follow-ons. An integration must preserve their scoring and execution contracts and demonstrate parity on representative outcomes. The default generated benchmark should run without either library installed. No plugin installation, host registration, or publication is part of the design-report phase.

## 11. Acceptance evidence for the rewrite

Validate the eventual skill from ordinary user inputs in fresh workspaces, with the authoring conversation withheld. Use a bounded cross-domain trial set rather than only reusing the old sealed suite:

| Trial request | Required observed behavior |
| --- | --- |
| Research workflow with a compact source corpus | Generates distinct assignments; runs the workflow; detects an unsupported but fluent report; accepts a well-supported alternative |
| Stateful support/planning agent | Resets each episode; permits multiple valid actions; checks preservation and required explanations; parallel episodes do not share state |
| Artifact-producing workflow, such as slides or an image brief | Inspects the actual artifact in the required modality; separates measurable constraints from subjective quality; labels unavailable judgments |
| Small coding workflow | Invokes the workflow on realistic change requests; grades delivered behavior; does not present runner tests as capability results |
| Slow or unreliable command/API adapter | Demonstrates bounded overlap, deadline cleanup, durable partial results, correct retry accounting, and resume without silently duplicating completed trials |
| Description-only request or missing execution capability | Produces a useful provisional package and explicit execution gap; makes no invented empirical claim |

For runner mechanics, use deterministic stand-ins to measure serial versus concurrent overhead and inject setup, timeout, and grading failures. For the skill's benchmark claim, include real bounded agent executions and inspect their artifacts. Measure setup, wall time, and grader overhead rather than inferring speed from the presence of `async`.

The rewrite is ready when another agent can create and exercise these benchmarks from declared inputs, the results distinguish useful differences without rejecting valid alternatives, and the documented costs and limitations match observations. A tiny pilot may validate mechanics and expose defects; it does not establish universal coverage or precise model rankings. Required work after this report is implementation, those bounded trials, one independent review, and evidence-based repairs.
