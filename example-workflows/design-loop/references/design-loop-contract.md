# Design iteration handoff

The [design-loop](../skills/design-loop/SKILL.md) coordinator owns cycles and checkpoints. Establish [library context](library-context.md). Each component performs only its stage from this context and its declared inputs. Composition stays in the caller; production may run directly, continue a suitable maker or use `orchflows:orch-work`, honoring named-assignment settings and common plus Make guidance. Shared comparison uses `orchflows:orch-review`.

## Request context

Carry the endgoal, observable success criteria, constraints, authorized workspace, source/reference paths, output directory, selected guidance, scoped model/effort choices and bounds. Preserve choices without adding model defaults. State assumptions for unspecified criteria or tools before dependent work; missing information that prevents meaningful or authorized work is a gap.

## State and records

Keep records in the caller's output directory, outside immutable snapshots. Use Markdown or the project's format; link artifacts instead of duplicating them.

| Record | Required content |
| --- | --- |
| Run checkpoint | Request context, N, attempt-start records and attempts started/completed, active cycle/stage, accepted state identity, artifact links, decisions, remaining bounds and stop reason. |
| Baseline | Exact initial or last accepted state: absolute path, stable identity, relevant files/configuration, environment and reproduction instructions. Include uncommitted and relevant untracked work; a differing working tree needs more than a commit ID. |
| Candidate | Separate editable baseline copy, frozen and identified after implementation; changed artifacts and reproduction instructions. |
| Stage handoff | Cycle/stage, input artifact/state identities, result, evidence links, assumptions and gaps; explicitly mark unexecuted stages. |
| Decision | Analysis recommendation, orchestrator's adopt/retain decision and reason, exact chosen state, goal progress and next-brainstorm observations. |

Before editing, preserve a reproducible baseline, including existing work, and create an isolated candidate. An empty workspace is valid. Accepted state changes only through the orchestrator's recorded adoption. Keep baseline and frozen candidate unchanged during testing and analysis; use disposable copies for side-effecting checks. Bind state identities and evaluation plan before testing. Store harnesses and evidence separately; candidate, environment or harness changes invalidate affected evidence.

## Comparison and adoption

Design fixes required checks and expected improvement before implementation. Compare identified states with the same relevant harness, inputs and controlled conditions; record identities, commands or observation procedure, environment, results and limitations. Separate expected old-state deficits from regressions. If the old state cannot run a new-feature check, report that and assess candidate correctness separately; invent no baseline score. Distinguish missing, failed and inapplicable checks.

Recommend adopt only when evidence supports required checks, preserved prior behavior and the increment's acceptance criteria. Otherwise recommend retain, explaining failures or gaps. The orchestrator checks exact states, criteria and evidence and records its decision without another agent review. Retention preserves the accepted state and carries unsuccessful ideas, observations and gaps forward.
