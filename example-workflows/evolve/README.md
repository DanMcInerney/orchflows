# Evolve

Improve code, designs, writing, generated media, prompts, workflows or other artifacts. Supply an artifact or a creation brief; the workflow designs its own evaluation when you have not supplied one. A numerical score and a target threshold are optional.

The default is one challenger against the current best. Wider tournaments are optional. Each experiment leaves evidence and a checkpoint; a plateau changes the search instead of ending it. The workflow can also test and adopt changes to its own working instructions, tools and search strategy.

```text
infer evaluation → make challenger → independently compare → retain best
                         ↑                                ↓
                         └──── evidence + checkpoint ─────┘
```

Examples after installing:

- `Use evolve:evolve on this poster. Make it better.`
- `Use evolve:evolve to improve this game's FPS while preserving gameplay. Run for an hour.`
- `Use evolve:evolve to develop cover art from this brief. Keep improving until I stop you, including how you generate it.`
- `Resume evolve:evolve from <run-directory>. Try three challengers per round.`

Without a duration or continuation request, a run defaults to three rounds. An explicit continuous request removes the round cap. The host must keep executing or resume the checkpoint; Markdown cannot schedule itself. Running indefinitely does not guarantee indefinite gains.

## Composition and cost

[evolve](skills/evolve/SKILL.md) uses core's `orch-work` for makers and `orch-review` for independent judges. Creating a seed from a brief uses one maker. Ordinary rounds use W makers (default W=1), one reviewer for a metric finalist, or one judge per subjective comparison plus one fresh confirmation for a proposed winner. Harness experiments replace an ordinary round: one proposer plus two makers per test case, with the same judging costs. The coordinator creates evaluation without a separate planning agent. Screening precedes expensive validation; width, repetitions and work limits are recorded before dispatch.

[Evaluation](skills/evolve/references/evaluation.md) owns scoring design and promotion. [State](skills/evolve/references/state.md) owns continuation and evidence. [Trials](trials/) contain reusable requests and expected behavior, not proof of results.

[Research](RESEARCH.md) documents the original Orchflows sources, Self-Harness, AIDE², SIA, Continual Harness and related work checked September 13, 2026, with design decisions and limitations.

## Install and dependencies

From a complete orchflows checkout, run `python scripts/orchflows.py setup --example evolve` with Python 3.11+. Setup preserves an existing library. Register and install `evolve` from the resulting home catalog using core `docs/hosts.md`; setup alone does not make a skill available by name.

Requires orchflows 0.7.0+, native child delegation, and tools that can create and inspect the requested artifact. There is no additional runtime or mandatory scoring service. Image, audio, browser or other capabilities depend on the task. Package context is resolved through [library-context](references/library-context.md).

This is a fresh successor to the original `orch-evolve`; `orch-` remains reserved for core skills. It supports experiments on improving an improvement harness. An RSI Level 1 claim would additionally require evidence of sustained gains over a strong human baseline on unseen tasks at matched cost; shipping this workflow does not establish that result.
