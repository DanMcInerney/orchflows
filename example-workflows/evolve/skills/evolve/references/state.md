# State and continuation

Use ordinary files in the run directory; no extra scheduler, database or workflow runtime is needed. The coordinator is the sole journal/checkpoint writer. Snapshots may be commits, copied files or immutable exported assets; paths alone are insufficient when contents can change.

Keep:

| Record | Contents |
| --- | --- |
| `brief.md` | Target, caller constraints, inferred preferences, resolved dependencies, bounds, per-experiment limits and stop conditions. |
| `evaluation/<version>/` | Complete evaluator, development and reserved inputs, baseline calibration and environment. |
| `harness/<version>/` | Working instructions/tools/search policy actually applied and parent revision. |
| `experiments/<id>/` | Hypothesis, parent identities, candidate snapshots, native child handles, outputs, raw measurement/judge evidence and decision. |
| `journal.jsonl` | Append-only events: experiment ID, phase, artifact/harness/evaluation identities, evidence paths, outcome and observed cost. |
| `checkpoint.json` | Run status, last committed decision, next experiment, incumbent/original/previous identities, active evaluation and harness, small archive, compact lessons, in-flight work, attempted rounds, observed usage relevant to caller limits, and remaining bounds. |

Record an experiment and its handles before waiting; record returned artifacts before judging. Commit a promotion by first writing its evidence and decision to the journal, then replacing the checkpoint via a temporary file. Retain the previous checkpoint until the replacement succeeds. Never change the incumbent in place.

On resume, read the brief, checkpoint and journal tail; verify referenced content identities and active versions. Reconcile any decision journaled after the checkpoint instead of promoting twice. Inspect saved native handles: rejoin live work, recover completed outputs, or mark confirmed lost work interrupted before retrying. Unknown liveness blocks that slot; never dispatch a duplicate blindly. Do not run two coordinators over the same run directory.

Interruptions are not losses. A half-written candidate, unavailable judge or unavailable confirmation remains unpromoted. Preserve the last verified incumbent and an explicit next action. Retain failed-experiment summaries to avoid repeating them, but keep raw evidence out of the active prompt. Reclaim reproducible scratch only after preserving required snapshots and evidence; never discard the sole copy of a retained artifact.

For continuous requests, keep taking experiments while execution is available. Checkpoint at every decision and before context rollover or host interruption. Use a host-supported continuation mechanism only within the caller's request and its tool contract; a new scheduler is not part of this library. Without such a mechanism, return a truthful resumable state. Resuming continues the saved budget and history unless the caller changes them.
