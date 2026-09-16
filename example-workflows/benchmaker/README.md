# Benchmaker

Build a benchmark around substantial user work: representative tasks, appropriate environments, useful partial credit and measured difficulty. Start with a prototype, calibrate a pilot and evaluate unseen source groups as evidence and budget permit. Each generated package states its requested and achieved stage.

**Experimental, version 0.2.1.** The 0.2 series adds [quality and acceptance gates](references/quality-profile.md) and retains the 0.1.1 integrity repairs. Version 0.2.1 clarifies control and record checks after fresh 0.2.0 trials; those final clarifications have not had another authoring replay. Cross-domain acceptance remains incomplete; see [validation status](trials/README.md). Harness checks, benchmark validation and agent measurement are separate evidence, not interchangeable readiness claims. The original [design report](DESIGN.md) is retained as historical rationale, not required invocation context.

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

Supply the target or capability, workspace and any budget or comparison constraints. Ordinary choices are inferred. A description-only request can produce a useful draft; absent target execution remains a measurement gap. For broad substantial-work claims, plan roughly 40–60 independently sourced development cases and a later 150–300-case evaluation suite; these are adjustable planning ranges, not statistical minimums or automatic launch budgets. A smaller prototype is labeled honestly and retains the larger request's unmet gates. Smoke, quick and full profiles select runs without changing maturity.

Challenge requests use a development objective of 30–50% full success for a named strong baseline, unless specified otherwise. This is separate from mean partial credit and representative-work performance. Cases need source-work provenance, substantive dependencies and feasibility evidence; small renamed fixtures cannot establish breadth. Freeze baselines and source-group splits before measurement, investigate failures, and publish unseen results even outside the desired band. Semantic scoring remains provisional until independent held-out calibration supports it.

## Composition and dependencies

The coordinator researches, designs and constructs in the caller context. One fresh `orch-work` pilot worker audits public inputs before seeing references, then exercises the package. One fresh `orch-review` reviewer assesses the frozen package and pilot evidence. One bounded repair pass follows; an affected independent rerun may use one additional worker. Two planned child calls, at most three, plus separately budgeted benchmarked agent executions. There is no automatic second review. Missing delegation leaves dependent validation incomplete.

Requires Orchflows core 0.7.0+ and native delegation; see [library context](references/library-context.md). The library itself has no runtime dependency beyond its host. Generated benchmarks prefer installed runtimes and, for new standalone runners, Python standard library and `asyncio`. Rendering, browsers, providers, containers and judges are added only when the task needs them. Bench-stack and Inspect integration are optional future work; neither is bundled.

The library supplies authoring instructions and [execution/data contracts](references/benchmark-contract.md), not a universal runner template. Generated packages, trial runs and evidence live outside the installed library in the caller workspace. Outputs include a benchmark card, cases/fixtures, target adapter, graders/controls, reproducible commands, raw evidence and a report with coverage and limitations. Local staging alone does not protect evaluator secrets from agents with broader filesystem access.

## Maintainer validation

Use the [trial specifications](trials/README.md) in fresh workspaces with the authoring conversation withheld. Packaging checks establish installation and discovery; only observed trials establish workflow behavior. The repository integration test copies and resolves this library in an isolated home and checks package-local links. No host registration or plugin installation is needed to inspect or edit this example.
