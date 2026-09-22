---
name: playtest-3d-browser-game
description: Independently assess an exact Three.js build through browser play, mechanics, QA and rendered assets; no repairs.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md), [test interface](../../references/test-interface.md) and [evidence](../../references/evidence.md). Resolve `core` or `final` scope; standalone review uses the supplied game's scope. Require the brief, source/build identity and runnable location/commands.

Use `orchflows:orch-review` once; final review uses a different reviewer from core. Supply applicable common/Review guidance, exact candidate, conditions, test route/scenarios and evidence location. Freeze edits or isolate the candidate/server. Provide public instructions first; reserve maker explanations, previous findings and QA evidence until first ordinary play reaches an outcome or observed blocker.

Assign the reviewer:

1. Confirm the served candidate and actual browser input/rendering capabilities; record conditions and limits. Install/run only declared project requirements.
2. Attempt first play from public instructions and rendered feedback through an outcome or blocker before reading design notes. Disclose earlier private-note exposure and label subsequent play informed.
3. Then complete adaptive play, diagnostic scenarios and regressions under playtesting Review guidance.
4. For `core`, judge graybox mechanics, decisions, readable feedback and full-loop feasibility without demanding production art. For `final`, also inspect runtime assets, motion, UI/loading/outcomes, supported audio and measured performance. Claim target performance only where the environment supports it; otherwise mark it unverified.
5. Save an evidence-linked report of episodes, coverage, findings, causal gameplay impact, useful changes, contradictions and limits, concluding ready/needs change/unverified. Never infer passes from a checklist.

The reviewer makes no undocumented game-state edits; reports, captures and isolated test artifacts are allowed. Return their paths; add no judgment round.
