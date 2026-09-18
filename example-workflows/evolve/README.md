# Evolve

Give Evolve an artifact and say what matters. It creates challengers, independently compares actual outputs, and retains only confirmed improvements. Code, posters, writing, media, prompts and workflows are supported when the host can create and inspect them. A creation brief produces an initial seed. Missing evaluation is inferred; numeric scores and target thresholds are optional.

## Use

After [installation](#install), invoke `$evolve:evolve` in Codex or `/evolve:evolve` in Claude Code:

```text
$evolve:evolve Improve this game's FPS while preserving gameplay and
visual quality. Run three rounds with one challenger per round. Use
./evolve-runs/game-fps/ for artifacts and evidence. Return the best version,
the measurements behind each decision and the checkpoint for resuming.
```

Other requests can improve a poster while preserving event details, develop cover art from a brief, run within a time budget, or resume a saved directory with several challengers per round. The workflow is manual-only by default.

## Promotion

1. Preserve the original and save calibrated evaluation before challengers.
2. Make isolated candidates from concrete hypotheses about the current best.
3. Screen failures, then measure or inspect actual outputs in their required medium.
4. Confirm wins independently. Subjective promotion needs two fresh judges with reversed presentation order; metric promotion needs a fresh audit of measurements and required checks.
5. Record evidence and checkpoint the decision. Failed requirements, missing evidence, ties and unconfirmed wins retain the incumbent.

The [evaluation contract](skills/evolve/references/evaluation.md) defines promotion. Evaluator repairs create a new version and require re-evaluation of contenders; scores across versions are not comparable progress. [Guidance](guidance/evolve.md) supplies search methods and budget planning.

## Improving the process

The **harness** is the working instructions, tools and search policy. A [harness experiment](skills/evolve/references/harness.md) replaces an ordinary round: reserve a known failure, prior success and fresh representative case before the proposer sees validation inputs, then test old and proposed procedures independently under matched conditions.

Adoption requires confirmed output improvement, preserved requirements and acceptable recorded cost. Accepted revisions govern later makers; contradictory evidence restores the predecessor. Candidates cannot change purpose, evaluation, promotion rules, budgets or checkpoint ownership.

## Bounds and continuation

[Evolve](skills/evolve/SKILL.md) coordinates in the caller. Ordinary production follows core staffing rules; judgments use `orch-review`, while harness proposals and validation require fresh contexts. Default bounds are **three rounds, one challenger per round**. Wider subjective tournaments can require additional comparisons; confirmation must fit the recorded work limits.

Each artifact or harness attempt counts before proposal or production, including failures and interruptions. Seed creation, calibration and evaluator repair spend resource budgets without adding or resetting rounds. An explicit continuous request removes the total round cap. After three informative rounds without promotion, the approach changes or the failure is investigated. A target stops work only when the caller makes it a stop condition.

The host must keep executing or resume the checkpoint. Without continuation capability, Evolve returns saved state and the gap; continuous requests do not guarantee continuous gains.

## Saved result

Return includes the best artifact, improvements and evaluation version, active harness, evidence, observable resource use, stop reason and resume path. Measurements, judge preferences and untested possibilities remain distinct.

Records use the chosen directory or `evolve-runs/<run-id>/`:

```text
brief.md          Purpose, constraints, bounds and assumptions
evaluation/       Versioned evaluators, inputs and calibration
harness/          Working process and revisions
experiments/      Hypotheses, snapshots, evidence and decisions
journal.jsonl     Append-only events
checkpoint.json   Best artifact, active versions and next action
```

The original, current best, previous best and promising alternatives survive. The [state contract](skills/evolve/references/state.md) governs interrupted work and resumption without budget resets.

## Install

From an Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example evolve
```

Setup preserves existing library copies. Register and install `evolve` from the home catalog using core `docs/hosts.md`, then start a new session. File creation alone does not establish availability by name.

Requires Orchflows 0.12.0+, native child delegation, and tools for the artifact's creation and inspection. No additional runtime or scoring service is mandatory; image, audio and browser needs depend on the task. See [library context](references/library-context.md).

[Trials](trials/) specify expected behavior, not observed results. Apply core's synthetic-input and simulated-effect policy for authoring trials. [Research lessons](references/research.md) inform design but do not validate this implementation. RSI Level 1 remains unestablished; it would require sustained gains over a strong human-assisted baseline on unseen tasks at matched cost.
