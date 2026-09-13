# Browser game playtesting

## Make

Prepare a test route an agent can actually use on this host: ordinary input and screenshots/motion, plus inspectable diagnostic controls. Put scarce timing-sensitive actions within the tool's capabilities using bounded held input or explicit time stepping for diagnostics. Keep ordinary real-time play available and label any assisted run. Test a concrete action with the real browser before committing to the route.

Use named scenarios for hard-to-reach cases, seeded randomness where feasible and state snapshots that help explain failures. Scenarios should initialize legal game states and then execute normal rules. Keep setup shortcuts distinguishable from evidence of player reachability. Record which tested states were entered naturally and which were injected.

## Review

Separate four questions: do the rules work, can a player understand/control them, do choices sustain interest, and does the rendered game hold up on the stated target? Scripts and state hooks answer parts of the first; they cannot stand in for the others.

Begin with the public instructions alone. Attempt to identify the goal, begin, act and interpret consequences before reading maker explanations or solutions. Then play a complete session adaptively: observe the rendered situation, state a short intent, apply a bounded ordinary input, inspect what changed and choose the next action. Include at least one change of plan caused by observation. Adjust action duration to feedback speed; blind long input sequences are coverage scripts, not adaptive play.

After first play, use design notes, scenarios and state summaries to diagnose. Exercise success/session completion, failure or setback, recovery and restart as appropriate; use different strategies, deliberately waste or hoard a resource, test boundaries and try to defeat the intended tradeoff. Visit the consequential branches and explain omissions. A win alone does not prove fairness or depth.

Inspect actual images and motion from the game: assets at gameplay scale, camera occlusion, animation/feedback timing, HUD legibility and start/outcome states. Listen when judging audio; report unreviewed audio if unavailable. Capture and inspect the game's canvas as well as relevant UI. A moving overlay cannot prove a frozen 3D scene is functioning.

Record observations and contrary evidence before concluding. Findings identify the build, scenario, reproduction steps, expected versus observed behavior, player impact and supporting captures/logs. Rank broken/blocked play before substantial clarity, fairness or strategy defects, then lesser polish. Report limitations plainly; do not infer a human enjoyment score or device-wide performance from a few agent sessions.
