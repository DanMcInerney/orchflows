# Benchmaker

Build benchmarks for substantial user work: representative tasks, faithful environments, useful partial credit and measured difficulty. Progress from prototype to calibrated pilot to evaluation on unseen source groups; each package reports its requested and achieved stage.

**Experimental, version 0.4.4.** Cross-domain acceptance remains incomplete; [validation status](trials/README.md) records replay coverage. Harness checks, benchmark validation and agent measurement are separate evidence. The [current design](DESIGN.md) explains the process; [quality gates](references/quality-profile.md) govern acceptance.

## Use

From an Orchflows checkout:

```sh
python scripts/orchflows.py setup --example benchmaker
```

Register the home and install `benchmaker` using core `docs/hosts.md`, then start a new session. Copying files does not register a skill. Invoke `$benchmaker:benchmaker` in Codex or `/benchmaker:benchmaker` in Claude Code; both default to manual invocation.

```text
Build a benchmark for this customer-support agent.
Compare these two research workflows; keep a quick run under five minutes.
Benchmark agents that turn a brief into a slide deck.
Make a benchmark for planning with changing resource constraints.
```

Supply the target or capability, workspace, budget and comparison constraints. Ordinary choices are inferred. A description supports a draft; measurement requires execution.

For broad substantial-work claims, planning defaults are 40–60 independently sourced development cases and a later 150–300-case evaluation suite. These are adjustable ranges, not statistical minimums or launch budgets. A smaller prototype retains the larger request's unmet gates. Smoke, quick and full select runs without changing maturity.

Challenge requests default to 30–50% full success for a named strong baseline on development cases. This differs from mean partial credit and representative-work performance. Cases require source provenance, substantive dependencies and feasibility evidence. Baselines and source-group splits freeze before measurement; unseen results are published even outside the target band. Semantic scoring remains provisional until independent held-out calibration.

## Process and dependencies

The coordinator authors and freezes the package, arranges a fresh pilot audit with public inputs before evaluator disclosure, gathers target measurements, then applies core `orch-review-revise-once` with a different reviewer. At most one repair pass follows; affected independent checks use the remaining allowance. The original review remains tied to its inspected version.

Requires Orchflows core 0.11.0+ and native delegation; see [library context](references/library-context.md). Missing capabilities leave dependent claims incomplete. No extra execution runtime is required. Generated runners prefer installed tooling or Python standard library and `asyncio`; rendering, browsers, providers, containers and judges are task-specific. Bench-stack and Inspect integration are unbundled future work.

Generated packages follow the [execution/data contract](references/benchmark-contract.md), with a benchmark card, cases, fixtures, adapters, graders, controls, reproducible commands and raw evidence. Outputs belong in the caller workspace. Local staging does not protect evaluator secrets from agents with wider filesystem access.

## Maintainer validation

Apply core `docs/hosts.md#workflow-trials` to the [trial specifications](trials/README.md): use fresh contexts, synthetic fixtures and simulated external effects; keep supplied references read-only. Required agent executions and judgments remain real. Simulation validates local behavior, not live integrations.

The repository integration check copies and resolves this library in an isolated home and checks package-local links. Packaging establishes discovery; observed trials establish behavior. Inspecting or editing this example needs no host registration.
