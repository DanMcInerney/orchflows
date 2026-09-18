# Browser game

Apply these criteria within the requested work and phase.

Design around a player verb and an interesting decision under constraints. The same action should create different consequences as space, information, resources or opponents change. Ask what the player observes, predicts, commits, risks and learns. A new skin, larger number or extra collectible does not by itself add a decision.

Mechanics need interacting rules and at least two viable approaches whose advantage changes with circumstances. For example, carrying more salvage could reduce acceleration, making a hazardous shortcut valuable only with a light load; a defensive move might also reposition an obstacle but spend a resource needed later. These illustrate interacting rules, not required genres. Preserve the caller's fantasy and chosen mechanics; do not force combat, bosses, timers or scoring onto a different game.

Make skill visible: a beginner can cause something useful, a practiced player can predict and improve, and mistakes produce understandable consequences with a chance to recover when the design allows. Avoid obligatory busywork, waiting that carries no decision, and progression that repairs deliberately unpleasant starting controls.

Use a small number of systems deeply. Give threats, tools and spaces distinct roles and counterplay. Teach one idea in a forgiving situation, test it, combine it with another and offer a mastery challenge. Alternate pressure and relief deliberately. Rewards should support future choices rather than only inflate a score.

Define enough content and variation to sustain the intended session. Completion includes entry, learning, the core loop, an ending or meaningful session boundary and replay. A single level can have substantial depth; a long feature list can still be a toy. Respect any explicitly bounded prototype phase without mislabeling it a finished game.

Build test access with the game: ordinary usable controls, understandable player feedback, stable action semantics and reproducible diagnostic scenarios. Test helpers expose and exercise the real rules. They must not silently replace collision, AI or win conditions with simplified test behavior.

The finished experience includes a clear start flow, contextual teaching, legible HUD, pause/settings, understandable outcomes and quick retry. Handle loading/progress/error states, unavailable rendering and input changes. Anticipation, response and consequence should read at gameplay speed through animation, sound and VFX as appropriate. Provide volume/mute and motion controls where needed and redundant cues for essential information. Polish must preserve actionable cues and responsive input. Judge legibility at the target resolution and camera, not only in enlarged captures.

Require separate evidence for correctness, adaptive play, art in runtime and performance under stated conditions. Treat agent enjoyment observations as qualitative evidence, not proof of a human audience's preferences.

## Make

Extract the fantasy, audience, target conditions, controls, session length, difficulty, visual tone, distribution and required features. State what the player repeatedly decides, what improves with mastery and what ends a session. Distinguish the complete release from optional expansion. Choose depth and finish over feature count.

Compare candidate mechanics by their main verb, constraint, competing choices, risk/reward, feedback, skill ceiling and system interactions. Describe a concrete 30-second episode, a way each idea could become boring or exploitable and a cheap experiment to expose it. Cosmetic variants of one loop do not count as different mechanics. Choose using agency, interacting rules, readable consequences, feasibility and testability; explain the tradeoff.

Develop the second-to-second action, session loop and longer progression where appropriate. Specify costs, recovery, loss, success, restart and learning through play. Document controls/state transitions and tunable parameters in a diagram and table. Identify the highest-risk assumptions, then plan scenarios with an action, expected player-visible consequence and failure signal before building all content.

Use a small graybox arena/course/puzzle set that exercises introduction, complication, combination and mastery. Connect actual progression and collision through a complete session, rather than assembling disconnected features. Add content variety by changing relationships, space, information and tradeoffs before increasing health, speed or counts. Tune economies and unlocks only when needed; keep content data separate from rule code.

Tie tuning to a hypothesis: "The full load is too safe, so the shortcut never matters; increasing braking distance should make route choice depend on cargo." Compare the same situation before and after, retaining adverse observations. Shorten or simplify a weak feature before compensating with more content. Prioritize goal/control confusion, dominant strategies, unfair setbacks, softlocks and unrecoverable states when making repairs.

## Review

Play the actual candidate before judging its design. Explain what decisions were available and why you changed strategy. Look for one-action dominance, unreadable consequences, fake choice, empty progression, unfair setbacks, friction in retry and repetitive pacing. Support criticisms with an observed episode and a causal explanation; list aesthetic preferences separately.

Judge the result against the brief and session scope. Verify that the central mechanic, promised interaction and complete session actually exist. A polished render does not compensate for an absent core loop.
