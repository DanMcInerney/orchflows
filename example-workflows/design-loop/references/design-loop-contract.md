# Design iteration handoff

The [design-loop](../skills/design-loop/SKILL.md) coordinator owns cycle scheduling and the run checkpoint. Reuse or establish the design context in [library context](library-context.md). Every component works independently from the inputs below and its declared stage inputs, performing only that stage. A composing skill runs in its caller; only `orch-work` and `orch-review` launch agents. The orchestrator chooses assignments under core execution rules.

## Request context

Carry the endgoal; observable success criteria; constraints and authorized workspace; relevant source/reference paths; output directory; selected guidance; scoped caller model/effort choices; and bounds. Preserve supplied choices through composition without adding model defaults. If criteria or tools are unspecified, state practical assumptions before dependent work. Missing information that prevents a meaningful or authorized result is a gap.

## State and records

Keep records in the caller's output directory, outside immutable state snapshots. Markdown or an existing project format is enough; fields may link to artifacts instead of duplicating them.

| Record | Required content |
| --- | --- |
| Run checkpoint | Request context, N, attempts started/completed, active cycle/stage, accepted state identity, artifact links, decisions, remaining bounds and stop reason. |
| Baseline | Exact initial or last accepted state: absolute path, stable identity, relevant files/configuration, environment and reproduction instructions. Preserve existing uncommitted and relevant untracked work. A commit alone is insufficient when the working tree differs. |
| Candidate | Separate editable copy derived from the baseline, then a frozen state identity after implementation. Identify changed artifacts and how to reproduce the result. |
| Stage handoff | Cycle/stage, input artifact and state identities, result, evidence links, assumptions, and gaps. Mark an unexecuted stage explicitly. |
| Decision | Analysis recommendation, root's adopt/retain decision and reason, exact chosen state identity, goal progress and observations for the next brainstorm. |

Before editing, preserve a reproducible baseline and create an isolated candidate; include existing work without overwriting it. An empty initial workspace is a valid baseline. Accepted state starts at this baseline and changes only on the root's recorded adoption. Keep baseline and frozen candidate unchanged during testing and analysis; run side-effecting verification in disposable copies. Before testing, bind both state identities and the evaluation plan. Store harnesses and evidence separately; a changed candidate, environment or harness invalidates affected comparison evidence.

## Comparison and adoption

The design defines required checks and expected improvement before implementation. Test the identified old and new states with the same relevant harness, inputs and controlled conditions; record state identities, commands or observation procedure, environment, actual results and limitations. Distinguish an expected old-state feature deficit from a regression. When the old state cannot run a new feature check, report that fact and evaluate candidate correctness separately; do not invent a baseline score. Missing, failed and inapplicable checks are distinct.

Analysis recommends adopt only when required checks have supporting evidence, prior required behavior is preserved, and the scoped increment meets its acceptance criteria. Otherwise recommend retain and explain the failure or evidence gap. The root checks the recommendation against the exact states, criteria and evidence, then records the decision; this adds no agent review. Retention keeps the prior accepted state and carries unsuccessful ideas, observations and gaps into the next cycle.
