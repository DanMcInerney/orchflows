# Browser game playtesting

Separate four questions: do the rules work, can a player understand/control them, do choices sustain interest, and does the rendered game hold up on the stated target? Scripts and state hooks answer parts of the first; they cannot stand in for the others.

Adaptive play means observing the rendered situation, choosing an intent, applying bounded ordinary input, inspecting the consequence and deciding the next action. Include a change of plan caused by observation. Adjust action duration to feedback speed; blind long input sequences are coverage scripts, not adaptive play.

Cover ordinary entry through completion and retry, failure/setback with recovery, consequential mechanic/content branches, alternate strategies and exploit attempts. Exercise pause/focus loss, resize, repeated restart, resource exhaustion, asset failure and saved-state behavior where applicable. Keep genuine play separate from deterministic scenario/seed coverage and diagnostic assistance; explain omissions. A win alone does not prove fairness or depth.

Inspect actual images and motion from the game: assets at gameplay scale, camera occlusion, animation/feedback timing, HUD legibility and start/outcome states. Listen when judging audio; report unreviewed audio if unavailable. Capture and inspect the game's canvas as well as relevant UI. A moving overlay cannot prove a frozen 3D scene is functioning. Review graybox and finished art against their respective phase, not the same finish standard.

Cover the declared browser/device/input matrix and identify the actual conditions. Viewport emulation alone cannot establish touch/controller behavior or device performance. Diagnostics accompany rendered observations; an unvisited state is not a pass.

Record observations and contrary evidence before concluding. Findings identify the build, scenario, reproduction steps, expected versus observed behavior, player impact and supporting captures/logs. Rank broken/blocked play before substantial clarity, fairness or strategy defects, then lesser polish. Report limitations plainly; do not infer a human enjoyment score or device-wide performance from a few agent sessions.

## Make

Prepare a test route an agent can actually use on this host: ordinary input and screenshots/motion, plus inspectable diagnostic controls. Put scarce timing-sensitive actions within the tool's capabilities using bounded held input or explicit time stepping for diagnostics. Keep ordinary real-time play available and label any assisted run. Test a concrete action with the real browser before committing to the route.

Use named scenarios for hard-to-reach cases, seeded randomness where feasible and state snapshots that help explain failures. Scenarios should initialize legal game states and then execute normal rules. Keep setup shortcuts distinguishable from evidence of player reachability. Record which tested states were entered naturally and which were injected. Repeat scenarios across seeds/configurations that can expose bugs.

## Review

Begin with the public instructions alone. Attempt to identify the goal, begin, act and interpret consequences before reading maker explanations or solutions. Then play a complete session adaptively under the common criteria.

After first play, use design notes, scenarios and state summaries to diagnose. Deliberately waste or hoard a resource, test boundaries and try to defeat the intended tradeoff. Support judgments with observed episodes and keep uninformed first-play evidence distinct from later diagnostics.
