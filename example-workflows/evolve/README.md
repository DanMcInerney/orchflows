# Evolve

**The next draft has to beat your best.**

Give Evolve an artifact and say what matters. It makes a challenger, compares actual outputs through independent review, and promotes only a confirmed improvement. Code, posters, writing, generated media, prompts and workflows can all be targets if the host can create and inspect them. A creation brief works too: the workflow makes a starting artifact first.

You do not need to invent a scoring system before asking for better work. Evolve derives and records evaluation from the brief when you have not supplied it. A numerical score and a target threshold are optional.

```text
infer evaluation → make challenger → independently compare → retain best
                         ↑                                ↓
                         └──── evidence + checkpoint ─────┘
```

## Give it something to beat

After [installation](#install-and-dependencies), paste this into Codex:

```text
$evolve:evolve Improve this game's FPS while preserving gameplay and
visual quality. Run three rounds with one challenger per round. Use
./evolve-runs/game-fps/ for artifacts and evidence. Return the best version,
the measurements behind each decision and the checkpoint for resuming.
```

In Claude Code, use `/evolve:evolve` with the same request. The workflow is manual-only by default.

Other starting points:

| What you have | What to ask |
| --- | --- |
| A poster that is almost there | `$evolve:evolve Improve this poster for first-time conference attendees. Keep the event details exact.` |
| A performance problem | `$evolve:evolve Improve this game's FPS while preserving gameplay. Run for an hour.` |
| A brief without an artifact | `$evolve:evolve Develop cover art from this brief. Keep improving until I stop you, including how you generate it.` |
| An interrupted search | `$evolve:evolve Resume from ./evolve-runs/game-fps/. Try three challengers per round.` |

## How a version earns promotion

1. **Define better.** Preserve the original, separate binding requirements from qualities to improve, and save an evaluator before creating challengers. Check that the evaluator detects an obvious defect or meaningful contrast.
2. **Try a concrete hypothesis.** Make an isolated candidate from the current best. Optional wider tournaments explore distinct ideas; each maker owns its own candidate.
3. **Compare the actual work.** Screen cheap failures first. Measure runnable artifacts under matched conditions; inspect renders, listen to audio or exercise interactions when the medium calls for it. Makers never certify their own wins.
4. **Confirm, then keep.** A subjective winner needs a second fresh judge with presentation order reversed. A metric finalist receives an independent audit of the measurements and required checks. Missing evidence, failed requirements, ties and unconfirmed wins keep the current best.
5. **Save the lesson and continue.** Record evidence and a checkpoint after each decision. A plateau changes the approach instead of quietly lowering the standard.

The required [evaluation contract](skills/evolve/references/evaluation.md) defines scoring, judging and promotion. If evaluation itself needs repair, the workflow versions it and re-evaluates contenders; scores from different versions do not count as comparable progress. [Evolve guidance](guidance/evolve.md) supplies reusable search and proposal methods, including planning enough budget for confirmation.

## It can test a better way to improve

Sometimes the repeated failure is in the process: the maker prompt, tool choice, context selection or search strategy. Evolve can propose one small change to that working process, called its **harness**.

A [harness experiment](skills/evolve/references/harness.md) replaces an ordinary round. It reserves a known failure, a previously successful case and a fresh representative case before the proposer sees the validation inputs, then runs old and proposed procedures independently from matched starting artifacts. Adoption depends on confirmed output improvement, preserved requirements and acceptable recorded cost. Accepted revisions become the instructions for later makers; later contradictory evidence can restore the predecessor. The caller's purpose, evaluation, promotion rules, budgets and checkpoint ownership remain fixed.

## Search and confirmation

[Evolve](skills/evolve/SKILL.md) coordinates in the caller. Ordinary production can run directly, continue a suitable maker or use `orch-work`, honoring scoped settings. Judges use `orch-review`; harness proposals and validation retain their required fresh contexts. Let `W` be challengers per ordinary round, default **1**.

| Work | Required process |
| --- | --- |
| Create a seed | Make an initial artifact from the brief |
| Metric round | Produce challengers; independently audit a promising measured winner |
| Subjective comparison | Independent preference plus a second fresh judgment in reversed order before promotion |
| Harness experiment | Produce old/new outputs independently on matched test cases, then apply the same evaluation |

Subjective tournaments may need further comparisons to choose among qualifying challengers, so their total is variable. Cheap rejections skip expensive confirmation. The coordinator records width, repetitions and per-experiment work limits before dispatch, retaining the required confirmation before promotion.

Absent supplied bounds, a run defaults to **three rounds**. A durable attempt start counts each artifact or harness attempt before its proposal or production begins; failures and interruptions do not refund it. Seed creation, initial calibration and between-round evaluator repair consume resource limits without adding or resetting artifact/harness rounds. An explicit continuous request removes the total round cap. After three informative rounds without a promotion, the workflow changes its approach, investigates the failure or tests a harness change; all attempted rounds and spent resources still count against caller bounds. Reaching a target stops the run only when the caller made it a stop condition.

The host must keep executing or resume the checkpoint; Markdown cannot schedule itself. When execution is unavailable, the result is a saved state and an explicit gap. A continuous request does not guarantee continuous gains.

## What survives the session

The result includes the best artifact, what improved under which evaluation, the active harness, evidence, observable resource use, the actual stop reason and a resume path. Claims distinguish measurements, judge preferences and untested possibilities.

Run records live in your chosen directory or a distinct `evolve-runs/<run-id>/` under the workspace:

```text
brief.md          Purpose, constraints, bounds and assumptions
evaluation/       Versioned evaluators, inputs and calibration
harness/          Working process and its revisions
experiments/      Hypotheses, snapshots, raw evidence and decisions
journal.jsonl     Append-only experiment events
checkpoint.json   Current best, active versions and next action
```

The original, current best, previous best and a small set of promising alternatives are retained. The [state contract](skills/evolve/references/state.md) covers interrupted work, identity checks and resumption without silently resetting the budget.

## Install and dependencies

From a complete Orchflows checkout, using Python 3.11+:

```sh
python scripts/orchflows.py setup --example evolve
```

Setup preserves an existing library copy. Register and install `evolve` from the resulting home catalog using core `docs/hosts.md`, then start a new host session. Setup alone does not make the skill available by name.

Requires orchflows 0.12.0+, native child delegation, and tools that can create and inspect the requested artifact. There is no additional runtime or mandatory scoring service. Image, audio, browser or other capabilities depend on the task. Package context is resolved through [library-context](references/library-context.md).

## Evidence and lineage

[Trials](trials/) contain reusable requests and expected behavior, not proof of results. [Research](RESEARCH.md) documents the original Orchflows sources, Self-Harness, AIDE², SIA, Continual Harness and related work checked September 13, 2026, with design decisions and limitations. The cited research does not validate this implementation's performance.

This is a fresh successor to the original `orch-evolve`; `orch-` remains reserved for core skills. It supports experiments on improving an improvement harness. An RSI Level 1 claim would additionally require evidence of sustained gains over a strong human baseline on unseen tasks at matched cost; shipping this workflow does not establish that result.
