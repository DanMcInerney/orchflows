# Research lessons

Use these precedents as evidence when choosing an approach, then inspect primary sources relevant to the target. Research agents checked them on September 23, 2026, from papers, official posts and repositories, without reproducing results. Figures are as reported by each source.

## Building and admitting tasks

| Decision | Precedent and lesson |
| --- | --- |
| What admission rejects | [Terminal-Bench 2.0](https://arxiv.org/abs/2601.11868): kept 89 of 229 submitted tasks after about three reviewer-hours each. "Verified" means tests pass if and only if the outcome is acceptable, a human-written reference passes and no shortcut exists. CI requires the reference to pass and a no-op agent to fail. An agent told to cheat attacked every task, and humans read every trajectory. Version 2.1 still repaired 28 of 89 for dependency drift, resource limits that defeated valid approaches, and misspecification |
| Task size and scoring range | [METR task guide](https://taskdev.metr.org/): aim for about 6–8 expert hours with one main hard step. A very competent agent should score above 0.9 and a very incompetent one below 0.1. Avoid model scoring where possible. A non-author QA run looks for loopholes. [HCAST](https://arxiv.org/abs/2503.17354): hand-reviewing agent runs found hacks, scorer crashes and ambiguities that human QA missed; author time forecasts explained only about half the variance of measured human times |
| Tests from real changes | [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) removed 68% of sampled tasks for underspecified issues or tests that reject valid fixes. OpenAI's [2026 audit](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) still found material test flaws in 59% of hard remaining tasks and verbatim recall of reference patches. A [later audit](https://openai.com/index/separating-signal-from-noise-coding-evaluations/) estimated about 30% of SWE-bench Pro broken: tests written to validate one change are not implementation-agnostic standards |
| Fair hidden tests | [SWE-bench Pro](https://arxiv.org/abs/2509.16941): stating requirements and the interface hidden tests call raised solvability about threefold without revealing tests. Its private and commercial splits guard against training exposure |
| Hard to solve, easy to verify | [BrowseComp](https://arxiv.org/abs/2504.12516): build questions backwards from a hard-to-find fact so the answer is short and checkable. Reject questions that frontier models or brief searches solve. [FrontierMath](https://arxiv.org/abs/2411.04872): automatically checkable answers with under 1% chance of guessing |
| Hardness filters | [Humanity's Last Exam](https://arxiv.org/abs/2501.14249) kept questions that frontier models failed; its own audits found 15–18% expert disagreement, and a [FutureHouse audit](https://www.futurehouse.org/research/hle-exam) estimated about 29% wrong answers in biology and chemistry. FrontierMath later repaired or removed 42% of problems. Filtering against models selects for bad keys unless every reference is fully verified |
| Expert-authored work | [GDPval](https://arxiv.org/abs/2510.04374): occupational tasks averaging about seven expert hours, graded blind and pairwise against an expert's deliverable. Human graders agreed 70.8% of the time |
| Tool necessity and difficulty | [MCP-Universe](https://arxiv.org/abs/2508.14704) rejects tasks solvable without the tools or solved consistently within five tries, and grades by execution against live ground truth. [MCPMark](https://arxiv.org/abs/2509.24002): single-attempt success of 52.6% fell to 33.9% under `pass^4` |
| Skills | [SkillsBench](https://arxiv.org/abs/2602.12670) runs identical tasks with and without skills, accepted 22% of submissions, and forbids skills that leak task details. Curated skills added 16.6 points on average but made 16 of 84 tasks worse; self-written skills added nothing on average. Anthropic's [skill-creator](https://github.com/anthropics/skills) compares with-skill runs to a baseline and tests activation with should-trigger and near-miss queries |
| Simulated users | [τ²-bench](https://arxiv.org/abs/2506.07982): simulated users erred in 16–47% of conversations by domain. Constraining them with tools and observable state improved reliability. Measure simulator error and report `pass^k` |

## Grader integrity

| Decision | Precedent and lesson |
| --- | --- |
| Audit outcome validity | [Agentic Benchmark Checklist](https://arxiv.org/abs/2507.02825): 7 of 10 benchmarks had task-validity flaws and 7 outcome-validity flaws. On τ-bench airline, an agent returning empty responses scored 38%; SWE-Lancer could be passed by overwriting tests. Report trivial-agent results |
| Initial-state passes | [OSWorld issue 518](https://github.com/xlang-ai/OSWorld/issues/518): tasks passed with no action when the initial state already satisfied them. [Epoch](https://epoch.ai/blog/what-does-osworld-tell-us-about-ais-ability-to-use-computers) found about 10% of tasks seriously flawed and about 45% doable without the GUI skill being tested |
| Exploit classes | Seen in real evaluations: objects whose equality always holds, exiting before tests, patching the test framework's reports ([Anthropic](https://arxiv.org/abs/2511.18397)); skipping tests, decompiling references, shadowing libraries ([OpenAI](https://arxiv.org/abs/2503.11926)); editing tests and special-casing inputs ([ImpossibleBench](https://arxiv.org/abs/2510.20270)); reading future fixes from version history ([SWE-bench issue 465](https://github.com/SWE-bench/SWE-bench/issues/465)); retrieving answers from the web ([Cursor](https://cursor.com/blog/reward-hacking-coding-benchmarks)); overwriting timing functions and introspecting evaluator state ([METR](https://metr.org/evaluations/openai-o3-report/)) |
| How often agents cheat | ImpossibleBench: frontier models passed about half of deliberately impossible tasks by cheating; read-only tests and an explicit abort option reduced it. [METR](https://metr.org/blog/2025-06-05-recent-reward-hacking/): 30% of runs hacked where the scorer was visible versus under 1% elsewhere, and instructions not to hack left most hacking. Cursor: 63% of one frontier model's successful SWE-bench Pro runs retrieved the fix, and a sealed harness cut scores by up to 20 points |
| Tests versus usefulness | [METR](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/): automated grading ran 24 points above maintainers' merge decisions. Calibrate automated verifiers against holistic expert review on a sample |

## Measuring and comparing

| Decision | Precedent and lesson |
| --- | --- |
| Cost and baselines | [AI Agents That Matter](https://arxiv.org/abs/2407.01502): simple baselines often match costly agents; report cost with quality and align holdouts with the claimed scope. [HAL](https://arxiv.org/abs/2510.11977): reading logs found agents retrieving gold answers and hardcoding test solutions; more reasoning effort often did not help |
| Uncertainty | [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640): cluster standard errors by source, compare systems by paired differences, and size suites by power analysis. [Dror et al.](https://aclanthology.org/P18-1128/): analysis depends on metric and sampling assumptions |
| Discrimination | [Signal and Noise](https://arxiv.org/abs/2508.13144): the ratio of spread between systems to run noise predicts whether a benchmark's decisions hold. [Arena-Hard](https://arxiv.org/abs/2406.11939) reports separability as the share of system pairs with non-overlapping confidence intervals |
| Small subsets | [tinyBenchmarks](https://arxiv.org/abs/2402.14992): calibrated subsets rely on historical responses; an invented handful has no equivalent guarantee |
| Model judging | [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685): position, verbosity and self-enhancement bias |
| Contamination and saturation | [LiveCodeBench](https://arxiv.org/abs/2403.07974): dating tasks against training cutoffs exposes contamination. Canary strings leak into training data, so pair them with private tasks. [Benchmarks saturate](https://arxiv.org/abs/2602.16763), often within a few years; a spread of difficulty extends usefulness |
| Coverage and dimensions | [HELM](https://crfm.stanford.edu/helm/): use scenarios and multiple metrics rather than one score mixing unrelated abilities |

## Generating benchmarks and measuring them

| Decision | Precedent and lesson |
| --- | --- |
| Measured desiderata | [AutoBencher](https://arxiv.org/abs/2407.08351) scores generated benchmarks on difficulty, separability and novelty relative to existing benchmarks. [LLM-Powered Benchmark Factory](https://arxiv.org/html/2502.01683v1): verify correctness, diversity and difficulty |
| Known differences | [Bloom](https://alignment.anthropic.com/2025/bloom-auto-evals/): generated evaluations were validated by whether they separated deliberately altered models from baselines (9 of 10 behaviors) |
| Generator self-bias | [Silencer](https://arxiv.org/abs/2505.20738): generators favor their own family's outputs; generators disjoint from the evaluated systems, or several diverse ones, reduce the bias |

Useful implementation boundaries: [Inspect](https://inspect.aisi.org.uk/tasks.html) separates tasks, solvers and scorers; [HAL](https://hal.cs.princeton.edu/about) preserves complete agent conditions and cost/performance comparisons; [Harbor](https://docs.harborframework.com/core-concepts/tasks/overview) separates instructions, environment, solution and verifier. Reusing a suitable existing harness need not impose its infrastructure on every task.

For domain design, inspect [AppWorld](https://github.com/StonyBrookNLP/appworld) for state and collateral-change evaluation, [TravelPlanner](https://github.com/OSU-NLP-Group/TravelPlanner) for resource-grounded constraints, [τ-bench](https://github.com/sierra-research/tau-bench) for complete interactive episodes, and [DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench) for distinguishing report quality from citation support.
