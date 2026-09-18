# Game evidence

Keep reproducible findings and distinguishable candidates in the project. Use readable files and useful machine output; no ticket system or custom schema is required. Combine records and omit empty documents.

## Records

- **Design:** brief/assumptions, selected concept/alternatives, loops, parameters, content arc, target budgets and experiments.
- **Run guide:** dependency/runtime versions, install/build/preview/test commands, URL/port, controls, scenario/seed entry, source/export commands and build identity.
- **Assets:** source/GLB/dependency paths, provenance, dimensions/pivots/colliders, clips, budgets and inspected runtime views under the [Blender contract](blender.md).
- **Playtest:** candidate, conditions, sessions/coverage, findings, captures/logs, conclusion and limits.
- **Repairs:** finding IDs, shared causes, changes, new identity, affected checks and unresolved findings.

## Identity and conditions

Use a full commit only if it identifies all tested source. Otherwise hash relevant source/configuration/lockfile/assets and built files, excluding dependencies, caches and evidence. Embed source identity in the running build; record the served production directory or immutable preview URL. Commits alone omit dirty changes; screenshot names do not identify builds.

Freeze edits or give reviewers an exact copy and isolated server. Record browser, renderer/backend, viewport, pixel ratio, quality, seed/scenario, mode, throttling and assistance. Preserve original review identity after repairs; identify delivered-revision maker verification separately.

## Sessions

Record significant episodes, not every frame:

| Observation | Intent/input | Consequence | Interpretation/evidence |
| --- | --- | --- | --- |
| Visible situation before action | Attempt, reason and held duration | Actual feedback/state change, including failure/surprise | Why it mattered; inspected capture/clip and event reference |

Include applicable learning, consequential choice, changed plan, setback/recovery and outcome/retry. Preserve failed routes instead of replacing them with a successful script. Open captures supporting visual claims; use clips/sequential captures for motion/timing and listening for audio.

Label coverage **observed pass**, **observed fail**, **assisted only**, **scenario only** or **not exercised**. Cover start/learning, core interactions, important branches, session boundary, setback/recovery, restart, alternate strategy and exploits; explain genre-specific omissions. Separate automated checks from adaptive play and maker checks from independent review.

## Findings and conclusions

Material findings need stable ID, severity/player impact, build, setup/seed, minimal inputs, expected/actual behavior, evidence and affected requirement/assumption. Recommend the smallest causal fix without repairing. Preserve contrary evidence; distinguish suspicion from observed defect.

- **ready:** required work/checks are supported; minor polish may remain if it does not defeat the brief.
- **needs change:** observed material failure, including substantial fun/readability failure despite passing tests.
- **unverified:** missing evidence or capability.

Do not average these into a score. After repairs, link each finding to verification and identify the final build. Recheck affected camera, collision, animation timing, content and performance; old independent verdicts do not transfer.

## Performance

Record workload, warm-up/measurement duration, sample count, timing source, median/tail frame times/stalls, load conditions and relevant renderer counters. Identify hardware versus software/headless rendering. Frame callbacks measure scheduling, not presented 3D frames; inspect moving gameplay and profile stalls where possible. Manual-step throughput and idle menus cannot establish gameplay FPS. Missing target hardware limits the measurement.
