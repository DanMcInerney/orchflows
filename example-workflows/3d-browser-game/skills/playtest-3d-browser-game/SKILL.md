---
name: playtest-3d-browser-game
description: Independently assess an exact Three.js build through browser play, mechanics, QA and rendered assets; no repairs.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md), [test interface](../../references/test-interface.md) and [evidence](../../references/evidence.md). Resolve `core` or `final` scope; standalone review uses the supplied game's scope. Require the brief, source/build identity and runnable location/commands.

Use `orchflows:orch-review` once; final review uses a different reviewer from core. Supply applicable common/Review guidance, exact candidate, conditions, test route/scenarios and evidence location. Freeze edits or isolate the candidate/server. Provide public instructions first; reserve maker explanations, previous findings and QA evidence until first ordinary play reaches an outcome or observed blocker.

Assign the reviewer:

1. Confirm the served candidate and actual browser input/rendering capabilities; record conditions and limits. Install/run only declared project requirements.
2. Attempt first play from public instructions and rendered feedback through an outcome or blocker. Record comprehension, time to meaningful action, controls/camera, setback clarity and uncertainty before reading design notes. This run may satisfy step 3. Disclose earlier private-note exposure and label subsequent play informed.
3. Play a complete representative session adaptively: change a tactic because of an observation, reach an outcome and retry through ordinary input. Try another viable approach, setback/recovery and an exploit/dominant-strategy attempt. Adapt session boundaries to the genre under playtesting guidance.
4. Read maker/design notes, then run diagnostic scenarios and regressions. Distinguish natural reachability, injected fixtures and assisted play. Inspect rules, input lifecycle, camera/colliders, important branches, errors and repeated reset; record omissions.
5. For `core`, judge graybox mechanics, decisions, readable feedback and full-loop feasibility without demanding production art. For `final`, also inspect runtime assets, motion, UI/loading/outcomes, supported audio and measured performance. Claim target performance only where the environment supports it; otherwise mark it unverified.
6. Save an evidence-linked report of episodes, coverage, findings, causal gameplay impact, useful changes, contradictions and limits, concluding ready/needs change/unverified. Never infer passes from a checklist.

The reviewer makes no undocumented game-state edits; reports, captures and isolated test artifacts are allowed. Return their paths; add no judgment round.
