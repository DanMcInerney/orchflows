# Game notes and evidence

Keep enough evidence for someone else to reproduce a finding and distinguish candidates. Use a few readable files and machine output where helpful; no ticket system or bespoke validation schemas are required. Record artifacts in the project, never in this library.

## Working records

- **Design:** brief/assumptions, selected concept and alternatives, core loops, tunable parameters, content arc, target budgets and experiment observations.
- **Run guide:** dependency/runtime versions, install/build/preview/test commands, URL/port, controls, scenario/seed entry, source/export commands and build identification.
- **Asset list:** source and GLB paths, textures, provenance when applicable, dimensions/pivots/colliders, clips, budgets and inspected runtime views. The Blender reference owns the fields.
- **Playtest report:** candidate identity, test conditions, sessions and coverage, findings, captures/log paths, conclusion and limits.
- **Repair record:** finding IDs, shared cause, changes, new candidate identity and affected checks, with unresolved findings preserved.

Combine these where it stays readable. Do not generate empty documents solely to satisfy a list.

## Candidate identity

Use a full commit when it describes all tested source. If the workspace is dirty or not in Git, save a content manifest/hash of relevant source/configuration/lockfile/assets and built files, excluding dependencies, caches and evidence outputs. Include the source identity in the running build and report the served production directory or immutable preview URL. A commit alone cannot identify uncommitted changes; a screenshot filename cannot identify a build.

Freeze edits while a reviewer uses the candidate, or give it an exact copy with an isolated preview server. Record browser, renderer/backend, viewport, device pixel ratio, quality, seed/scenario, mode and any throttling/assistance. Keep the original review tied to its original identity after repairs; identify maker verification of the delivered revision separately.

## Session evidence

For ordinary or assisted play, record a few significant episodes, not every frame:

| Observation | Intent/input | Observed consequence | Interpretation/evidence |
| --- | --- | --- | --- |
| What the player could see before acting | What was attempted and why, with duration if held | Actual feedback/state change, including surprise or failure | Why the choice mattered; capture/clip and useful event reference |

Include the initial learning attempt, a consequential decision, a change of plan, a setback/recovery and the outcome/retry as applicable. Keep real failures and failed routes; do not replace them with the final successful script. Captures must be opened and inspected to support a visual claim. Clips or sequential captures are needed for motion/timing claims; listening is needed for audio claims.

Report coverage as observed pass, observed fail, assisted only, scenario only, or not exercised. Cover start/learning, core actions/interactions, important content branches, success/session boundary, failure/setback, recovery, restart, alternate strategy and exploit attempts. Adapt inapplicable states to the actual genre and explain that decision. Separate automated checks from adaptive play and maker checks from independent review.

## Findings and checkpoint conclusions

Give each material finding a stable ID, severity/player impact, build, setup/seed, minimal input steps, expected versus actual behavior and evidence. Recommend the smallest change that addresses the cause; reviewers do not repair. State which requirement or design assumption it affects. Preserve contrary evidence and distinguish an untested suspicion from an observed defect.

Use ready when required work and checks are supported, needs change for an observed material failure, and unverified when evidence/capability is missing. Do not average these into a quality score. Minor known polish issues may accompany ready if they do not defeat the brief. Substantial fun/readability failures are material, even when tests pass.

For performance, record the workload, warm-up/measurement duration, sample count, timing source, median and tail frame times/stalls, load conditions and renderer counters that matter. Identify hardware versus software/headless rendering. Frame callbacks measure scheduling intervals, not proof of presented 3D frames; inspect moving gameplay and use available profiling to explain stalls. Never report manual-step throughput or an idle menu as target gameplay FPS. Missing target hardware yields a limited measurement, not an invented pass.

After repairs, retain the review, link each finding to its verification and identify the final build. If a change affects camera, collision, animation timing, content or performance, rerun those relevant conditions. Do not silently transfer an old independent verdict to a changed game.
