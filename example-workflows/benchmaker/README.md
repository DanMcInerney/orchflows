# Benchmaker

Build a small runnable benchmark from an agent, workflow, command or capability description: representative tasks, appropriate environments, defensible grading and interpretable results. Each generated package makes a bounded claim and uses dependencies appropriate to its tasks.

**Experimental, version 0.1.0.** The workflow and acceptance scenarios are implemented. Cross-domain acceptance remains incomplete; see [validation status](trials/README.md). Harness checks, benchmark validation and agent measurement are separate evidence, not interchangeable readiness claims. The original [design report](DESIGN.md) is retained as historical rationale, not required invocation context.

## Use

From an Orchflows checkout, copy the example into an Orchflows home:

```sh
python scripts/orchflows.py setup --example benchmaker
```

This uses the repository's ordinary setup behavior. Register the home and install `benchmaker` with the host's normal plugin flow described in core `docs/hosts.md`, then start a new session. Writing or copying files alone does not register a skill. `/benchmaker` is the requested short name; fully qualified native invocations are `$benchmaker:benchmaker` in Codex and `/benchmaker:benchmaker` in Claude Code. Both hosts default to manual invocation.

Example requests:

```text
Build a benchmark for this customer-support agent.
Compare these two research workflows; keep a quick run under five minutes.
Benchmark agents that turn a brief into a slide deck.
Make a benchmark for planning with changing resource constraints.
```

Supply the target or capability, workspace and any budget or comparison constraints. Ordinary choices are inferred. A description-only request can produce a useful draft; absent target execution remains a measurement gap. The default authoring suggestion is roughly 12–24 cases, adjusted to the task. Smoke, quick and full profiles trade coverage and execution cost explicitly.

## Composition and dependencies

The coordinator researches, designs and constructs in the caller context. One fresh `orch-work` pilot worker audits public inputs before seeing references, then exercises the package. One fresh `orch-review` reviewer assesses the frozen package and pilot evidence. One bounded repair pass follows; an affected independent rerun may use one additional worker. Two planned child calls, at most three, plus separately budgeted benchmarked agent executions. There is no automatic second review. Missing delegation leaves dependent validation incomplete.

Requires Orchflows core 0.7.0+ and native delegation; see [library context](references/library-context.md). The library itself has no runtime dependency beyond its host. Generated benchmarks prefer installed runtimes and, for new standalone runners, Python standard library and `asyncio`. Rendering, browsers, providers, containers and judges are added only when the task needs them. Bench-stack and Inspect integration are optional future work; neither is bundled.

The library supplies authoring instructions and [execution/data contracts](references/benchmark-contract.md), not a universal runner template. Generated packages, trial runs and evidence live outside the installed library in the caller workspace. Outputs include a benchmark card, cases/fixtures, target adapter, graders/controls, reproducible commands, raw evidence and a report with coverage and limitations. Local staging alone does not protect evaluator secrets from agents with broader filesystem access.

## Maintainer validation

Use the six [trial specifications](trials/README.md) in fresh workspaces with the authoring conversation withheld. Packaging checks establish installation and discovery; only observed trials establish workflow behavior. The repository integration test copies and resolves this library in an isolated home and checks package-local links. No host registration or plugin installation is needed to inspect or edit this example.
