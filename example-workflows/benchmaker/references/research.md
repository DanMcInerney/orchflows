# Research lessons

Use these precedents to choose an approach, then inspect primary sources relevant to the target. Sources were checked September 16, 2026, without reproduction or independent validation. The similarly named BenchMaker project is separate from this workflow.

| Decision | Precedent and lesson |
| --- | --- |
| Task and outcome validity | [Agentic Benchmark Checklist, v5](https://arxiv.org/html/2507.02825v5): audit both; high/low target scores alone validate neither |
| Cost and generalization | [AI Agents That Matter, v1](https://arxiv.org/html/2407.01502v1): report quality with cost and align holdouts with the scope claimed |
| Generated cases | [LLM-Powered Benchmark Factory, v1](https://arxiv.org/html/2502.01683v1): verify correctness, diversity and difficulty; multiple-choice generation is not a general agent interface |
| Coverage and dimensions | [HELM](https://crfm.stanford.edu/helm/): use scenarios and multiple metrics, not one score mixing unrelated abilities |
| Small subsets | [tinyBenchmarks, v2](https://arxiv.org/html/2402.14992v2): calibrated selection uses historical responses; an invented handful has no equivalent guarantee |
| Model judging | [Judging LLM-as-a-Judge, v4](https://arxiv.org/html/2306.05685v4): account for position, verbosity and self-enhancement bias |
| Uncertainty | [Dror et al., ACL 2018](https://aclanthology.org/P18-1128/): analysis depends on metric and observation/sampling assumptions |

Useful implementation boundaries: [Inspect](https://inspect.aisi.org.uk/tasks.html) separates tasks, solvers and scorers; [HAL](https://hal.cs.princeton.edu/about) preserves complete agent conditions and cost/performance comparisons; [Harbor](https://docs.harborframework.com/core-concepts/tasks/overview) separates instructions, environment, solution and verifier. Reuse a suitable existing harness without imposing its infrastructure on every task.

For domain design, inspect [AppWorld](https://github.com/StonyBrookNLP/appworld) for state and collateral-change evaluation, [TravelPlanner](https://github.com/OSU-NLP-Group/TravelPlanner) for resource-grounded constraints, [τ-bench](https://github.com/sierra-research/tau-bench) for complete interactive episodes, and [DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench) for distinguishing report quality from citation support. A small local fixture may borrow the boundary without claiming to reproduce the full benchmark.

Bench-stack is not a runtime dependency or acceptance suite. Optional adapters must preserve upstream execution/scoring meaning and demonstrate outcome parity before claiming integration.
