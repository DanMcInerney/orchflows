---
name: playtest-3d-browser-game
description: Independently play and assess an exact Three.js game build, covering usability, mechanics, QA and rendered assets in one independent review without repairs.
disable-model-invocation: true
---

Reuse or establish [library context](../../references/library-context.md). Use a fresh reviewer who made none of the candidate; preserve uncoached first-play evidence. A final playtest uses a different reviewer from the core playtest. Resolve `core` or `final` scope from the caller; a standalone request reviews the supplied game's current scope. Require the brief, source/build identity and runnable location/commands. Read the [test interface](../../references/test-interface.md) and [evidence contract](../../references/evidence.md).

Use `orchflows:orch-review` once, with the applicable common quality criteria and Review guidance, exact candidate, conditions, test route/scenarios and evidence location. Freeze edits or isolate the candidate/server. Give the reviewer the public player instructions first, with maker explanations, previous findings and QA evidence reserved until its first ordinary run reaches an outcome or an observed blocker. Its assignment is:

1. Confirm the served candidate and actual browser input/rendering capabilities. Record conditions and limitations. Run/install only what the project's declared instructions require.
2. Attempt first play using only the public instructions and rendered feedback, through an outcome or an observed blocker. Observe comprehension, time to meaningful action, control/camera behavior and whether setbacks explain themselves. Record uncertainty before consulting design notes. Reuse a complete run for step 3's session requirement. If private notes were read earlier, state that boundary and label subsequent play as informed.
3. Play a complete representative session adaptively, including at least one changed tactic caused by something observed. Reach an outcome and retry through ordinary input. Try a different viable approach, a failure/setback with recovery, and an exploit/dominant-strategy attempt. Apply the playtesting guidance, adapting session boundaries to the genre.
4. Read the design/maker notes and run targeted diagnostic scenarios and regressions. Separate naturally reached states from injected fixtures and assisted play. Inspect rule outcomes, input lifecycle, camera/collider behavior, important branches, errors and repeated reset. Record coverage and missing cases explicitly.
5. In `core` scope, judge readable graybox mechanics, decisions, feedback and full-loop feasibility; do not demand production art. In `final` scope, also inspect integrated assets at gameplay scale, motion, UI/loading/outcome flows, audio where supported, and measured performance evidence under its stated conditions. Run performance checks only where the environment supports the claimed target; otherwise mark the target unverified.
6. Save an evidence-linked report with episodes, coverage, findings and ready/needs change/unverified conclusion. Explain the causal gameplay impact and most useful changes. Return actual observations, contradictions and limits, not a checklist with inferred passes.

The reviewer makes or delegates no repairs, edits no game state through undocumented shortcuts, and does not alter the candidate. It may write its report, captures and isolated test artifacts. Return the report and evidence paths to the caller; this leaf neither repairs nor launches another judgment round.
