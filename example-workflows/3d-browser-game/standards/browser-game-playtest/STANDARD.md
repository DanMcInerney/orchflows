---
name: browser-game-playtest
description: Stamp when ordinary-input play sessions and their provenance are judged as evidence for a browser game.
narrows: orch-research
adapter: git
---

An actual play session is an immutable JSON-lines transcript of interleaved
observation and ordinary keyboard or pointer input through the served game.
Each reply records sequence, monotonic and wall time, visible DOM facts,
read-only game snapshot, screenshot or hash where applicable, and
console/network deltas. The session identifies player context, browser,
workspace revision, controls, and capture coverage.

The provenance label stays explicit: adaptive input is `actual play`, a fixed
command list is `scripted input`, and fake time or state mutation is
`simulated`. Scripted or simulated material can support a narrow technical
check, but cannot support a play-quality claim. Maker-independent contexts
remain distinct, and their disagreements, dead ends, losses, and missing
coverage stay visible.

Reviewers examine ordinary-input reachability, control disclosure, learning,
challenge, choices, pacing, feedback, terminal or continuing states,
restart/re-entry, capture completeness, and transcript integrity. A session
with missing observations, altered state, ambiguous attribution, or a lost
trace is unverified regardless of its screenshots.
