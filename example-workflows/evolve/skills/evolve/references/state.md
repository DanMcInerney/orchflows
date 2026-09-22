# State and continuation

Use files in the run directory; the coordinator alone writes journal/checkpoint. Snapshot through commits, copies or immutable exports; mutable paths alone do not identify content.

| Record | Contents |
| --- | --- |
| `brief.md` | Target, caller constraints, inferred preferences, resolved dependencies, bounds, per-experiment limits and stop conditions |
| `evaluation/<revision>/` | Complete evaluator, development/reserved inputs, baseline calibration and environment |
| `harness/<revision>/` | Applied instructions/tools/search policy and parent revision |
| `experiments/<id>/` | Kind (artifact, harness or evaluation repair), hypothesis, parent identities, snapshots, native handles when used, outputs, raw measurement/judge evidence and decision |
| `journal.jsonl` | Append-only events: experiment ID, applicable attempt start, phase, artifact/harness/evaluation identities, evidence paths, outcome and observed cost |
| `checkpoint.json` | Status, last committed decision, next experiment, incumbent/original/previous identities, active evaluation/harness, archive, lessons, in-flight work, attempted rounds, informative nonpromotions since promotion, observed usage and remaining bounds |

One round is one artifact/harness attempt under core iteration bounds. Before proposal work, journal its ID, parent identities and updated count. Seed creation, initial calibration and evaluator repair spend resource budgets without adding/resetting rounds or authorizing a repair loop. Record them and active repairs.

Save native handles before waiting and returned artifacts before judging. Journal promotion evidence/decision before replacing the checkpoint via a temporary file; retain the previous checkpoint until replacement succeeds. Never edit the incumbent in place.

On resume, read brief, checkpoint and journal tail; verify content identities/revisions. Reconcile later journaled starts/decisions without losing attempts or informative-nonpromotion counts or promoting twice. Rejoin live handles, recover completed outputs, or mark confirmed lost work interrupted before retrying within the same round's limits. Unknown liveness blocks its slot. Never duplicate uncertain work or run two coordinators over one directory.

Partial candidates and unavailable judgments/confirmation remain unpromoted, not losses. Preserve the last verified incumbent and next action. Keep failed-experiment summaries in active context, raw evidence on disk. Reclaim reproducible scratch only after preserving snapshots/evidence; never discard a retained artifact's sole copy.

Continuous requests proceed while execution remains available. Checkpoint each decision and before rollover/interruption. Use only a host-supported continuation mechanism within caller authorization and tool contracts; otherwise return resumable state. Resumption preserves budget/history unless the caller changes them.
