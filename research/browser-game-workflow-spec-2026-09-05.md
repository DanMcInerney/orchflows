# Three.js and Blender browser-game workflow specification

The `browser-game` workflow has one production route: a 3D browser game using
a pinned Three.js dependency and assets authored with a pinned Blender
executable. Its order is deliberate: deep parallel research; detailed design
of the core idea, rules, fun loop, and game concept; a fundamental playable
Three.js game with functional placeholder assets; separate QA, adaptive play,
and a demanding independent core-gameplay gate; GPT concept art and production
Blender assets after that gate; integration; and a second demanding whole-game
gate. Each gate can judge, fix, QA, play, and re-judge repeatedly until its
evidence is good enough. This document specifies that reusable workflow. It
does not implement the workflow or build a game.

All **MUST**, **SHOULD**, and **MAY** statements are proposed workflow policy.
Statements labeled **Current fact** report primary documentation checked on
2026-09-05. A run rechecks facts whose pinned Blender, Three.js, browser,
graphics backend, or model identity has changed. Recommendations are defaults
to test, not guarantees about an unmeasured project.

## Outcome and completion contract

The public workflow remains `browser-game`. It takes `brief`, the user's
complete natural-language request, and `workspace`, the target git repository.
Three.js and Blender are fixed by this workflow. The original brief, together
with explicit user amendments made during the run, is the authority for game
promises. Concept revisions clarify how to satisfy that authority; they never
silently replace it or turn a generic example into a new requirement. The
workflow must not invent promises about browser support, hardware,
accessibility, licensing, monetization, telemetry, or release.

The workflow has two distinct acceptance identities:

1. **Core-gameplay acceptance** proves that the fundamental game works, is
   understandable, and is engaging enough to continue under ordinary input.
   Primitives, graybox geometry, and basic functional placeholders are allowed
   here. Final visual polish is deliberately outside this gate, while readable
   feedback, timing, camera behavior, sound or animation needed for fair play,
   and every central mechanic remain required.
2. **Whole-game acceptance** proves one integrated release candidate looks good,
   plays well, and adheres to the frozen original prompt. It includes approved
   concept art, production Blender assets, final content breadth, complete
   play and capture coverage, and the declared performance evidence. Attractive
   art cannot mask a weak core loop.

A successful final return contains:

- `artifact: git:<commit>` for the accepted game revision;
- an evidence-index identity binding the original brief and amendments,
  research, concept, core increments, asset manifests, play sessions,
  captures, performance traces, judgments, repairs, and both gate verdicts;
- the core and whole-game gate identities, including their fixed artifact
  revisions and coverage records;
- the exact outside probe and its passing observation at the joined commit; and
- `gaps: []`.

A core-gate return may be an intermediate handoff. A non-success final return
names the fixed artifact reached, all evidence gathered, each complaint or
unverified claim still open, the last completed quality-cycle batch, and the
exact resumable state. The final gate requires a browser-served production
build that starts without developer tools; documented controls; a coherent
brief-derived core loop; every promised mechanic, progression path, terminal
or continuing state, and replay or re-entry behavior; approved production
assets with closed provenance; no blocking console, network, or load errors;
actual adaptive play; independent acceptance; and every required performance
cell passing. A prototype, scripted state transition, screenshot gallery, or
green unit suite cannot satisfy either gate by itself.

Publishing, buying or accepting licensed assets, installing Blender or other
system software, and making commercial or support promises require current or
standing user authority. The future workflow may perform one authorized,
bounded setup step and resume its capability gate. This document-only revision
performs no installation, asset purchase, publication, or game implementation.

## Baseline and deliberate replacement

This revision is derived from the clean candidate baseline recorded by the
parent (`e3c3c11d9ea44b1acab1d70a30dc7a93809e7636`). The prior specification
revision recorded its own source baseline as
`bbdc7effbf00ed8f7d58eff1b422513bb9d1b9b2`; that provenance remains part of
the replacement history. An earlier draft covered
2D and 3D routes, compared engines, treated MCP as a possible Blender path,
and stopped after a fixed two-round review. This revision keeps the fixed
Three.js plus native Blender CLI/`bpy` stack, replaces engine or DCC choice with
capability checks, and makes the user's gameplay-first sequence and continued
quality cycle the contract.

The current public [browser-game workflow](../example-workflows/browser-game/SKILL.md)
already records a program, evidence, a checkpoint, and a successor plan. It
does not make assets or code, open playable increments, perform actual play,
gather presentation evidence, or judge a complete game. The rebuilt package
SHOULD preserve its atomic authority, immutable evidence identities, and
explicit invalidation while replacing its fixed questionnaire with the
research, core, and whole-game gates below.

## Package shape, ownership, and call flow

Only `browser-game` is public. The following proposed paths are private to
`example-workflows/browser-game/` (or to the corresponding project or user
ring package if authored there):

| Package path | Responsibility |
| --- | --- |
| `SKILL.md` | Public contract, stage order, frame ownership, quality-cycle progress, and close behavior. |
| `workflows/discovery/SKILL.md` | Brief audit, deep parallel research, fixed-tool probes, concept/rules freeze, and evidence matrices. |
| `workflows/playable-increment/SKILL.md` | One isolated build, QA, land, ordinary-input play, capture, and fixed-revision checkpoint. |
| `workflows/gameplay-gate/SKILL.md` | Core-gameplay evidence collection, demanding independent judgment, findings, and successor repair batches. |
| `workflows/blender-asset/SKILL.md` | One post-core production asset batch through source edit, inspection, render, export, validation, judgment, and handoff. |
| `workflows/final-acceptance/SKILL.md` | Whole-game evidence fan-out, independent judgment, bounded repair batches, re-judgment, and outside close. |
| `skills/blender-bpy/SKILL.md` | Reusable method for job-driven `bpy`/BMesh creation, editing, inspection, rendering, and export. |
| `standards/browser-game-3d-asset/STANDARD.md` | Private 3D game-asset root: source authority, budgets, manifest, previews, runtime handoff, and artifact evidence. |
| `standards/blender-game-asset/STANDARD.md` | Blender-specific narrowing of `browser-game-3d-asset`. |
| `standards/threejs-browser-game/STANDARD.md` | Three.js game-code narrowing of `orch-code`. |
| `standards/browser-game-interface/STANDARD.md` | Rendered canvas, menu, HUD, focus, and accessibility narrowing of `orch-design`. |
| `standards/browser-game-playtest/STANDARD.md` | Ordinary-input session and provenance narrowing of `orch-research`. |
| `references/` | Run-record, traceability, job, asset-manifest, evidence-index, capture-matrix, rubric, and worked-example contracts. |
| `scripts/` | Capability probes, Blender process launcher and worker, manifest/GLB checks, capture indexing, performance collection, and outside probe. |
| `tools.txt`, optional `requirements.txt`, `package.json`, lockfile | Tools and libraries used by package scripts only. Game dependencies stay in the target workspace. |

The public workflow opens one frame and drives private helpers in this order:

1. `discovery` audits the complete prompt and launches independent research
   lanes in parallel. It synthesizes their evidence into a detailed concept,
   traceability matrix, rubric, capture matrix, and core test plan. It uses
   written visual intentions and research references only; GPT concept art and
   production asset jobs wait.
2. `playable-increment` makes the Three.js core from the frozen concept. Its
   candidate uses primitives, graybox geometry, and basic functional
   placeholders, with enough feedback to test the intended mechanics fairly.
   The helper runs scoped QA and adaptive play, lands each accepted checkpoint,
   and records core evidence.
3. `gameplay-gate` reads a fixed core commit and the core evidence packet. Its
   maker-independent judge either accepts the fundamental gameplay or emits
   complaint IDs. A repair `do` receives the findings verbatim, runs QA and
   play again, and a successor batch re-judges while progress continues.
4. Only after core acceptance does the parent freeze the accepted
   mechanics/control/collision/camera/timing baseline, invoke GPT concept-art
   generation and inspection, and fan out post-core `blender-asset` jobs.
5. The parent lands those production assets, runs a Three.js integration
   increment, and checks animation timing, hitboxes, camera occlusion,
   silhouette/readability, motion feedback, disposal, and performance.
6. `final-acceptance` judges the fixed integrated candidate against the full
   capture matrix and every play account. It repeats QA, repair, adaptive play,
   and demanding re-judgment through successor batches until it passes or an
   actual stop condition is reached. The outside probe runs after all children
   return and prints the joined identity.

No helper calls another public workflow or recursively calls its own quality
cycle. Typed `artifact:` and `findings:` lines cross each handoff verbatim.
Each wave reads the frame journal before acting and lands completed work before
opening its successor. A standard carries domain knowledge only: it has no
stage order, delegation, stop condition, or return contract. `blender-bpy`
carries reusable technique and MUST declare `role: worker`; its host profile
owns the concrete model and effort.

The standard bases are deliberate. `threejs-browser-game` MUST declare
`narrows: orch-code`; `browser-game-3d-asset` is a private git-adapter root
because a `.blend`, GLB, manifest, structural inspection, and rendered review
need asset evidence; `blender-game-asset` narrows only that root. The interface
standard MAY narrow `orch-design` for rendered UI evidence and MUST NOT own
mesh, material, rig, or animation quality. The playtest standard MAY narrow
`orch-research` for a traceable evidence packet. Target Three.js dependencies
remain in the target workspace lockfile; package tooling owns none of them.

## Authority, traceability, and freezes

The run record indexes rather than transcribes work. It identifies the original
brief and explicit amendments; target-workspace baseline; host, Blender,
Three.js, browser, hardware, and backend capabilities; dated research packets;
concept revision; core and final acceptance matrices; every playable increment;
asset source/export manifest; play session; capture; performance cell; judge;
repair; and gap.

The immutable traceability matrix has at least these columns: prompt promise
and amendment identity; derived rule, state, content, or visual requirement;
playable evidence identity and normal-input path; core-gate verdict; final-gate
verdict; owner; and invalidation trigger. A promise with no rule or evidence is
an open hard gate. A concept revision adds a row or a new revision and names
invalidated descendants; it never edits the prompt or overwrites a prior
verdict. Generic genre conventions remain out of scope unless the prompt
adopts them.

Every decision records owner, evidence identity, revision, confidence, and
invalidation trigger. Product intent and promises are `kind: user-only`. Exact
installed versions, renderer/backend choice, collision route, asset budgets,
and test mechanics are empirical decisions. The brief revision, pinned
dependencies, core concept, control map, collision/camera/timing contract,
target hardware, acceptance dimensions, and core evidence plan freeze before
the core candidate. The production art direction and asset contracts freeze
after core acceptance against that accepted baseline. A contradiction creates
a new evidence and decision revision, names affected descendants, and resumes
at the earliest affected gate.

## Stages and literal gates

| Stage | Inputs | Output and gate |
| --- | --- | --- |
| 0. Deep research | Complete brief, amendments, workspace, baseline | Parallel dated research packets, prompt audit, capability inventory, and open-question ledger. Research may continue on supplied facts while a user-only gap parks only dependent decisions. |
| 1. Core concept design | Stage 0 identities and independent packets | Detailed fun hypotheses, rules/state model, controls/camera, progression/content plan, session test, traceability matrix, rubric, capture/performance matrices, and frozen core contract. No production art prerequisite. |
| 2. Fundamental playable game | Frozen core contract | Three.js playable increments I0–I2 with primitives, graybox, basic functional placeholders, normal input, readable feedback, scoped QA, and adaptive play. A tiny technical export/import probe may answer feasibility; it is not production art. |
| 3. QA and core-gameplay gate | Fixed core candidate and complete core evidence | Separate QA, at least two maker-independent play contexts, complete core captures, and a demanding independent verdict, with repeated judge/fix/QA/play/re-judge successor batches until core acceptance or a real stop; `redesign` routes to Stage 1 with a new concept revision, named invalidations, and a new core candidate, while `unverified` routes to missing-evidence acquisition or a capable execution context. |
| 4. Concept art and production assets | Accepted core identity and frozen baseline | Inspected GPT concept-art set, post-core Blender source/GLB batches, closed manifests, and integrated production candidate. Missing image or Blender capability parks only dependent work. |
| 5. Integration QA and whole-game gate | Fixed integrated candidate and final matrices | Production build, asset/runtime checks, full adaptive play and captures, declared performance cells, demanding whole-game verdict, and repeated repair successor batches until acceptance or a real stop. |
| 6. Outside close and resume | Joined fixed revision, returned children, verdict ledger | Outside probe, exact artifact identity, `gaps: []` only on acceptance, or best fixed revision plus unresolved findings and resumable state. |

### Deep research before design

Research launches one independent lane per material question cluster inside the
fixed Three.js-and-Blender scope: game and mechanic comparables; Three.js and
browser feasibility; Blender asset feasibility and budgets; and host play,
capture, and performance evidence. Each lane returns its question, source
policy, dated source identities, claims and counterevidence, authorized spike
observations, supported decisions, confidence, disagreements, and gaps without
reading another lane's packet. Synthesis waits for at least two independent
packets, correlates them rather than voting, and gives every ledger item an
answer or explicit gap under one evidence identity. Research does not compare
engines or DCCs.

The audit covers fantasy and audience; core and session loops; mechanics,
world/content structure, progression, terminal or continuing states, replay or
re-entry; controls, disclosure, and camera; target hardware/browser/display;
art, audio, UI, and accessibility scope; asset and license constraints;
delivery boundary; repository conventions; and the quality bar. The
capability inventory observes the exact pinned tools, available visual/input
control, capture and error-reading capability, and production-like serving.
Missing Blender or image generation is a capability gap. With standing
authority, the workflow may make one bounded setup attempt and re-probe.
Without authority, it returns the exact `kind: user-only` question and parks
only dependent work. A technical export/import probe is allowed when it
answers a feasibility question, with a distinct probe identity and no claim of
production art.

### Detailed core concept and design freeze

Synthesis produces a build-ready concept, not a genre label. Before making, it
states testable hypotheses such as “the player understands the main choice
within two attempts” or “escalating pressure creates a meaningful risk/reward
decision.” It defines what observation would support or weaken each hypothesis.
It freezes, as applicable:

- fantasy, purpose, fun loop, session shape, and the bounded full-session or
  continuing-loop observation goal;
- controls, input disclosure, focus, camera framing, camera movement, and
  recovery behavior;
- entities, ownership, mechanics, collision, rules, resources, timing,
  transitions, win/loss/continuing states, restart, and replay/re-entry;
- level/world topology, content breadth, spawn or encounter logic, progression,
  difficulty, pacing, challenge, choice, and learnable counterplay;
- feedback for actions, hits, damage, objectives, rewards, failure, and
  transitions, including the minimum sound/animation/UI needed for fair play;
- written art direction, reference sources, palette and silhouette intentions,
  accessibility direction, and placeholder contracts;
- asset/provenance and geometry/material/rig/texture budgets, target hardware,
  stress scenarios, and the vertical-slice plan; and
- core hard gates, critical gameplay dimensions, score anchors, evidence
  owners, capture cells, and regression checks.

This stage may inspect research references and write visual intentions. It does
not generate GPT concept art, require a concept-art review, or make production
Blender assets. Those activities start only after the core gate passes. A
placeholder represents a declared tested function and is listed in the core
evidence; it cannot hide an unimplemented central promise behind a stub.

### Fundamental Three.js game and placeholder milestones

The core candidate uses the target workspace's pinned Three.js and ordinary
browser input. Primitives and graybox assets must still provide legible
silhouette, scale, collision, timing, camera behavior, action/reward/failure
feedback, simple sound or animation where the concept needs it, and enough
content to test the intended choices. Final material polish, detailed meshes,
production textures, and a broad final cast are deferred. A viable Three.js
prototype does not wait for Blender; absent Blender parks only dependent
production asset work.

Each `playable-increment` begins at the last accepted commit, makes one bounded
candidate, runs seam checks and a production build, lands the checked commit,
serves that exact identity, and records ordinary-input play, captures, and
findings. The core milestones are:

| Increment | Required core proof |
| --- | --- |
| I0 control/state tracer | Production build boots; normal entry and canvas focus work; primary controls and camera work; one representative state transition crosses final input/state seams; a promised restart/re-entry path works; and a representative GLB or tiny export/import probe loads through `GLTFLoader` when relevant. |
| I1 fun-loop slice | Several minutes of adaptive ordinary-input play demonstrate the smallest complete loop, action and interaction feedback, intended challenge or expressive opportunity, and meaningful choice/progression where promised. Placeholder subjects, focal props, environment, animation, VFX, UI, and audio cover the mechanics under test. |
| I2 core-session candidate | The full bounded acceptance journey or continuing-loop window is reachable with every central mechanic, world/content topology, progression, terminal/continuing state, and replay/re-entry path. Placeholder inventory and concept-derived stress seeds are complete. |

QA, adaptive play, and judgment are separate records. QA fixes known
technical blockers before the independent judge sees the revision. Playtesters
receive current visual feedback, act on a normal clock, and adapt later input
to observations. A scripted sequence can support a narrow functional check;
it cannot support a fun or complete-game claim.

### Core-gameplay gate

The core gate freezes the I2 commit, prompt traceability matrix, concept and
rubric revision, QA result, play accounts, capture matrix, and representative
performance evidence before judging. Its hard gates are production boot,
focus and controls, fundamental loop, every central mechanic and state
transition, every promised core progression/content path, terminal or
continuing behavior, replay/re-entry where promised, functional final boss
play when central to the brief, readable feedback and fair camera/collision,
and no undisclosed placeholder masking an unimplemented promise. A deliberate
graybox is not a visual-polish failure at this gate.

At least two maker-independent agents or contexts play the fixed core commit
with ordinary input. Together they cover every required core path and state;
one begins at the normal entry surface and encounters controls/tutorial
disclosure. For a continuing game, the concept's bounded observation window
must be traversed. Each account and capture binds artifact commit, browser,
device/backend, seed, input mode, time, choices, state transitions, recovery,
readability, pacing, fun/frustration observations, and console/network result.

The core judge is independent of the maker and sees the fixed evidence index,
not maker conversation. It enumerates every required core capture and reads
every play account in full. It scores the frozen critical dimensions with
predeclared anchors: loop purpose and clarity; control/camera feel; interaction
feedback and state readability; fairness and challenge; meaningful choice or
progression; pacing and continued engagement; prompt fidelity; and stability.
Each dimension must be strong (normally at least 3 on a 0–4 scale) and every
hard gate must pass. A forgiving average cannot offset a weak critical
dimension. The verdict names strengths, complaint IDs and responsible seams,
contrary evidence, confidence, expected visible improvement, regression
checks, and one disposition: `pass`, `fix`, `redesign`, or `unverified`.

Core evidence is sufficient only when it proves the mechanics and loop through
normal play. Screenshots, simulated state jumps, attractive concept references,
and unit tests are supporting evidence with narrower meanings. Fun is an
evidence-backed judgment about this loop and these contexts; it is not a unit
test, screenshot claim, or proof that every player will enjoy the game.

## Post-core concept art, Blender assets, and integration

After the core verdict is `pass`, the parent records the accepted mechanics,
control, collision, camera, timing, and feedback baseline as immutable input to
production. GPT image generation then produces the required concept-art set.
The record binds provider/model identity, prompt revision, inputs,
rights/restrictions, output hashes, and view coverage. A visual-capable maker
and separate inspector view every candidate, record rejections and risks, and
freeze selected silhouettes, views, scale cues, palette, materials, and lighting
by identity for affected jobs. References guide production; they never prove a
`.blend` or runtime asset.

Post-core Blender jobs use the native CLI subprocess and the `blender-bpy`
method. Every job has a never-reused directory/id, explicit input hashes,
source mode, seed, unit/axis/pivot contract, allowlists, budgets, render
cameras, export options, and expected outputs. Procedural jobs treat generator,
job JSON, and pinned references as authority; edited jobs treat the pinned
`.blend` as authority and record one-purpose edit provenance. Production
concept art, representative production Blender assets, and mass art production
are all downstream of the accepted core identity.

Asset inspection includes the gameplay camera and a fixed turntable, plus
animation frames where relevant. Validation records structure, transforms,
bounds, ground contact, topology, materials, textures, armatures, clips,
budgets, source/export hashes, and a machine-readable Khronos glTF report.
`GLTFLoader` integration checks scale, orientation, materials, clip playback,
bounds/collider alignment, load errors, and representative-device cost. A
failure promotes nothing and receives a new job id. Missing image inspection or
Blender parks the dependent production batch while the accepted core remains
valid.

The integration increment replaces placeholders only through accepted asset
manifests. It checks animation timing against gameplay events, hitboxes and
colliders, camera occlusion, silhouette and readability at gameplay distance,
motion feedback, scale/material drift, UI/audio integration, disposal, and
performance. An art change that alters collision, timing, camera, control, or
other gameplay behavior invalidates the affected core verdict and routes back
to the core evidence plan. Late gameplay defects receive gameplay repair;
cosmetic work cannot conceal them.

## Whole-game evidence and demanding final gate

The final gate freezes one integrated release-candidate commit before review.
Maker-independent lanes collect deterministic build/mechanics results,
production asset/provenance manifests, visual captures, ordinary-input play
accounts, compatibility/console/network results, and physical-device traces.
Collectors do not edit the candidate.

The final capture matrix covers every required viewport and DPR at boot,
loading, errors, normal entry/control disclosure, opening play, each mechanic,
progression/content phase, representative session or continuing-loop state,
visual stress/readability condition, pause/settings surface, terminal or
continuing state, and replay/re-entry. Inapplicable cells need a frozen
rationale. Every capture binds commit, viewport/DPR, browser/backend, state,
seed, and timestamp. Every play account is read in full. Missing coverage,
unread accounts, broken identities, or unresolved conflicts are unverified hard
gates; curated subsets cannot pass.

Final hard gates cover clean production boot; controls/focus; all prompt and
concept promises; every mechanic, content and progression path; terminal or
continuing behavior; replay/re-entry; zero undisclosed placeholders or
blocking errors; asset provenance and disposal; complete capture and adaptive
play coverage; and every required performance cell with callback/Chrome-frame
agreement. The final judge scores, with frozen 0–4 anchors, prompt fidelity;
loop and purpose; controls/camera; feedback/readability/fairness; challenge,
choice, pacing, and continued engagement; level/world coherence; 3D art,
silhouette, animation, and motion coherence; promised UI/audio/accessibility;
stability; and polish. The concept may omit a dimension only with a recorded
reason. Every applicable dimension must be strong and every hard gate must
pass. The final review re-runs the affected core proof against the accepted
baseline; a core regression blocks final acceptance. There is no reward for
attractive art masking weak mechanics and no
false rejection of the deliberately scoped core graybox.

The final maker-independent judge names strengths, material complaints and
causes, contrary evidence, confidence, expected visible improvement, regression
results, coverage omissions, and conflict resolution. It classifies each
finding as defect, unverified claim, or preference. Preferences do not block
unless the frozen prompt or rubric makes them material. A material unresolved
complaint, weak critical score, conflict, or missing evidence yields `fix`,
`redesign`, or `unverified`, never a rubber-stamped pass.

## Quality-cycle progress, repair, and resumption

Both gates use the same durable quality cycle: freeze the judged artifact and
critical dimensions; collect QA, actual play, and independent judgment; record
complaint IDs; hand accepted findings to one repair; run scoped QA; repeat
affected play and evidence; and re-judge the fixed revision. The complaint
ledger is append-only. A repair goal names only accepted complaints, their
responsible seams, affected evidence, expected visible improvement, and the
regression subset. A re-judge repeats every affected gate plus a smoke subset
of unaffected paths. It compares the before/after evidence and closes a
complaint only when the expected improvement is visible and no regression is
introduced.

Each individual ticket or frame uses a bounded repair batch for context and
resource control. **Where the judge blocks, one repair `do` is handed the
`findings:` line verbatim, then one re-judge; two rounds is the bound.** That is
a local batch bound, not an automatic total stop for the public workflow. When
a batch remains blocked but the parent is authorized, making progress, and has
not reached a user/host budget or time boundary, the parent opens an automatic
successor batch with the complete ledger and fixed criteria. It never creates
a recursive private workflow cycle, silently relaxes a threshold, resets the
complaint ledger, or asks permission merely to open an already-authorized
successor.

A `redesign` disposition routes to Stage 1 with a new concept revision, named
invalidations, and a new core candidate. An `unverified` disposition continues
through missing-evidence acquisition or a capable execution context. Neither
disposition is an independent terminal reason: either becomes a non-success
return only when its recorded cause also meets one of the enumerated real stop
conditions, preserving the best fixed revision, unresolved ledger, and exact
resume state.

Stagnation, reopened complaints, or oscillation trigger independent diagnosis
and a materially changed repair or design plan. The diagnosis preserves the
original prompt, critical dimensions, evidence, and failed approaches. It may
return `redesign` when the frozen concept cannot make the promise testable or
enjoyable. Repeating the same action without new causal evidence does not count
as progress. Stop only for acceptance; user cancellation; an applicable
user/host budget or time boundary; or an evidenced external, unresolvable
blocker. At a stop, return the best fixed revision, unresolved findings,
contrary evidence, confidence, and exact resumable state.

The frame journal is read at every wave head. A crash or context loss resumes
through `orchflows resume`, resolves the recorded package and evidence
identities, lands completed outcomes, and reopens only absent or expired
dispatches. **Close on a command run outside every child; never on a child's
own claim.** The outside probe checks the joined commit, installs/builds from
the workspace lockfile, serves production output, exercises boot, normal entry,
representative mechanics/state transitions, and replay/re-entry through
ordinary input, and validates the complete gate coverage and complaint ledger.

## Native Blender job boundary

**Current fact:** Blender's command line can run without a UI, execute a Python
file with `--python`, turn an uncaught command-line script exception into a
chosen nonzero status with `--python-exit-code`, and pass following arguments
untouched after `--`. Blender evaluates arguments in order ([command-line
arguments](https://docs.blender.org/manual/en/5.1/advanced/command_line/arguments.html)).

The default route launches the absolute, capability-probed Blender executable
as a fresh subprocess for one job. The host runner builds an argument array,
sets an explicit wall timeout, and owns process-tree termination:

```text
<BLENDER_EXE> --background --factory-startup --python-exit-code 23 --python <PACKAGE>/scripts/blender_asset_job.py -- <JOB_DIR>/job.json
```

The worker gets variable input from `job.json`; it does not receive generated
Python through `--python-expr` or open a socket. One Blender process owns one
`.blend` state. Concurrent jobs never share a writable source or output path.
CPU jobs use a measured process cap; GPU renders serialize per GPU by default.

The worker prefers `bpy.data` and BMesh for deterministic edits. Operators are
used only at supported boundaries such as open, save, render, and export, with
scene, view layer, mode, active object, selection, engine, device, frame, and
output path asserted before use. Structural inspection records names, external
references, units, transforms, bounds, geometry, UVs, normals, materials,
textures, armatures, clips, poses, and budgets. The source, export, render,
executable, OS/driver/backend, job, and manifest identities are bound even
where GPU output cannot be byte-identical.

The handoff keeps `.blend` as source and `.glb` as runtime delivery. Its
manifest fixes meters, exported +Y up, gameplay-forward vector, origin,
transforms, bounds, collider/attachment metadata, material and texture roles,
animation names/ranges, skeleton/morph budgets, required decoders/extensions,
and hashes. The runner promotes outputs only when Blender exits zero, echoed
job and input digest match, outputs are new, contained, nonempty and
hash-matched, inspection/render evidence is complete, the pinned Khronos
validator reports no errors, and the pinned production `GLTFLoader` path
passes scale/material/animation/collider checks. A timeout, mismatch, partial
file, validator error, or import mismatch promotes nothing.

Blender's pip-installable `bpy` module MAY be used only after pinning a
compatible distribution and passing the same render/export/signal/timeout
probes. It remains one disposable worker process and is never assumed
compatible with the Orchflows interpreter. The executable subprocess remains
the default. These native rules are unchanged by the gameplay-first order.

## Three.js runtime contract

Before I0, the concept assigns each system to an explicit seam: normal-clock
simulation and pause/visibility handling; ordinary input and focus; collision
and camera; boot/loading/active/pause/phase/terminal/replay states; entity and
content ownership; `GLTFLoader` progress/errors/decoders; animation mixer and
clip cleanup; renderer, materials, color management, culling, LOD, instancing,
particles, and post-processing; audio unlock/mixing/disposal; DOM/canvas UI,
HUD, accessibility, resize/DPR, and resource disposal. Load errors are visible
game states and test seams.

Three.js and all runtime decoders or physics dependencies are pinned in the
target workspace lockfile. A manifest using Draco, Meshopt, or KTX2 names its
loader setup and decoder identity; omission or load failure is fatal. Removal
disposes geometries, materials, textures/image bitmaps, render targets,
skeletons, mixers, listeners, and audio according to ownership.

Renderer choice is empirical inside the fixed Three.js route. The default
acceptance baseline SHOULD use pinned `WebGLRenderer` on WebGL 2.
`WebGPURenderer` MAY replace it only when the exact revision, materials,
fallback, browsers, captures, and performance cells pass. A backend change
invalidates visual and performance evidence. Color inputs, working space,
output transform, tone mapping, environment maps, and post-processing are
explicit. Instancing and animation strategies require measured draw-call,
memory, and peak-density evidence rather than assumed benefit.

## Actual adaptive playtesting

The target carries a small browser harness that starts/stops server and
browser, focuses the game, issues ordinary keyboard/pointer actions, waits on
a normal clock, returns a current screenshot plus a compact read-only state
snapshot, and starts/stops capture. It may use Playwright's ordinary input
APIs ([Playwright input](https://playwright.dev/docs/input)) or an equivalent
host. It never invokes game methods to move the player, grant progression,
advance content, or set terminal/continuing state.

Evidence labels are explicit:

- **actual play:** current visual feedback, sustained ordinary input on a
  normal clock, and later input adapted to observations;
- **scripted input:** a fixed ordinary-input sequence without adaptive
  observation; and
- **simulated:** fake time, scenario jumps, direct state mutation, bots, or
  headless/null rendering.

Only actual play supports play-quality and complete-game claims. A session
records artifact commit, harness/browser/device/backend, seed, real start/end
time, input mode, checkpoints/captures, actions and choices,
mechanic/progression/state transitions, recovery or re-entry, control problems,
pacing, readability, feedback, fun/frustration observations, console/network
errors, and confidence limits. Both main gates require at least two
maker-independent play contexts and all applicable account/capture coverage.
If no available agent can see and control real-time play, the workflow records
`actual-play: unverified`, preserves narrower evidence, and cannot claim the
affected gate passed.

## Real presented-frame performance

“60 fps” is a measurement cell. Each cell binds device/CPU/GPU/RAM, OS and
power mode, browser/version, renderer/backend, display refresh, viewport/DPR,
quality settings, commit, scenario/seed, warm/cold state, duration,
instrumentation, raw paths, metric definitions, thresholds, and invalidation
rule. The core gate proves representative active-play and worst-core-scenario
cells; the final gate adds every production stress and full-session cell.

A stationary menu/pause surface must stay stable, error-free, and responsive to
a marked ordinary-input transition; Chrome idle frames receive no 59 fps
threshold unless continuous menu motion is promised. Required animation cells
use brief-derived motion or a visible sentinel rendered through the game
canvas. The default 60 Hz contract uses three warm 60-second runs per bounded
animation/stress scenario after warm-up.

For an animation run, let `T` be the complete marked foreground normal-clock
window in seconds. `requestAnimationFrame` evidence must average at least 59
callbacks per second over `T`, place at least 99% of callback intervals at or
below 18.33 ms, and contain no unexplained stall above 100 ms. Callback cadence
is necessary but does not prove compositor presentation.

**Current fact:** Chrome's protocol exposes `Tracing.start` with `traceConfig`
and `ReturnAsStream`, `Tracing.end`, and `tracingComplete` with a stream and
`dataLossOccurred` ([CDP Tracing](https://chromedevtools.github.io/devtools-protocol/tot/Tracing/)).
The collector preserves raw stream/completion metadata, pins and probes Chrome,
CDP schema, format, categories, and parser, and pads both sides of the marked
window.

**Current fact:** Pinned DevTools `FramesHandler` uses Meta, Renderer, and
LayerTree handlers; consumes `BeginFrame`, `DrawFrame`, `DroppedFrame`,
`RequestMainThreadFrame`, `BeginMainThreadFrame`, `Commit`/legacy
`CompositeLayers`, `ActivateLayerTree`, `NeedsBeginFrameChanged`, and
`SetLayerTreeId`; and emits `TimelineFrameModel` timing plus `idle`, `dropped`,
and `isPartial` ([pinned source revision](https://github.com/ChromeDevTools/devtools-frontend/blob/9f9f40ba5bca7e385be30535cdbf01a3a7e5ba44/front_end/models/trace/handlers/FramesHandler.ts)).
Partial and dropped flags may overlap, and omitted undrawn non-dropped frames
mean row count is not exhaustive display opportunity evidence.

Before accepting a cell, discovery qualifies static-idle,
continuous-game-animation, and deliberate-stall traces. It proves padded
extraction, `dataLossOccurred: false`, clock reconciliation, raw joins,
game-canvas renderer/layer attribution, flag overlaps, and stall failure. A
negative fixture keeps callbacks or another compositor layer active while
delaying canvas draws; the game-cadence claim must fail. Unparsed formats,
loss, ambiguous attribution, or incomplete coverage make dependent cells
`performance: unverified`.

For a qualified animation window, `N` counts unique rows starting in
`[start, end)`; `C` counts rows attributed to the game canvas and free of
`idle`, `dropped`, or `isPartial`; `I` counts idle rows; and `D` counts rows
with `dropped OR isPartial`, once when both. Passing requires `N > 0`,
`C / T >= 59`, `D / N <= 1%`, and the callback thresholds. Static windows
report `N`, `I`, and flags without this denominator. Callback and clean-frame
thresholds must agree on scenario, seed, markers, duration, and artifact.
Fake clocks, background tabs, throttling, null renderers, fast-forward, and
dev builds are diagnostic only. A repair targets the measured bottleneck and
repeats the identical cell; lowering resolution, content density, effects,
browser cohort, or hardware target requires a visible decision revision.

## Failure and resumption table

| Event | Required behavior |
| --- | --- |
| Missing product promise | File one `kind: user-only` question verbatim; continue independent research and park only dependent design/build work. |
| Changed prompt or amendment | Freeze a new authority revision, update traceability, name invalidated descendants, and resume at the earliest affected gate. |
| Missing/changed Blender, browser, image, or tool | Record observed and required capability; perform one authorized bounded setup/re-probe or return the exact user-only question. Invalidate dependent evidence on identity change. |
| Image generation or inspection unavailable | Record `concept-art: unverified`; park only post-core art jobs and retain viable core gameplay evidence. |
| Blender job failure | Preserve job, source, script/package identity, stdout/stderr, partial outputs, and diagnosis; promote nothing; retry only as a new job. |
| Three.js load/runtime failure | Keep candidate unlanded, bind console/network/manifest evidence, repair the responsible seam, and refresh QA before judgment. |
| Agent cannot see/control play | Preserve scripted/simulated evidence with its narrower label; dispatch a capable context or return actual play unverified. |
| Core judge block | Record findings verbatim, run a scoped QA/fix/play/re-judge batch, and open a successor batch while authorized progress continues. |
| Production art changes gameplay | Invalidate affected core verdict and route to gameplay repair and re-judgment before final acceptance. |
| Final judge block | Apply the same durable quality cycle; diagnose stagnation or redesign when complaints reopen or oscillate. |
| Performance miss/contradiction | Preserve raw callbacks and trace, attribute one bottleneck, repair one seam, and repeat the identical cell. |
| Stagnation or external limit | Record diagnosis, unchanged evidence, budget/time or external proof, best fixed revision, unresolved findings, and exact resume state; never relax quality silently. |
| Crash/context loss | Use `orchflows resume`, read the frame journal, resolve recorded identities/package digest, land completed outcomes, and reopen only absent or expired dispatches. |
| Package changes mid-run | Refuse stale admission and start a successor run citing predecessor evidence; never mix package contracts. |

## Worked invocation: one-level 3D survivor game

```text
/browser-game build me a 3d vampire survivors-like game with 1 level but many waves that ends in a final boss fight
```

Deep research launches independent lanes for survivor pacing and boss
counterplay, Three.js entity/runtime feasibility, Blender production budgets,
and host adaptive-play/performance capture. The audit treats 3D, one level,
many waves, and a final boss as fixed prompt promises. A reversible proposal
might be a 12-minute local run, keyboard movement with automatic attacks, an
original stylized low-poly direction, and pinned Chromium/WebGL 2 as the first
60 Hz cell. Exact support remains user-owned.

Design then fixes testable fun hypotheses, an arena with landmarks and spawn
exclusions, controls and camera, attack/damage/experience/upgrade/spawn/death/
win/restart states, grace/escalation/relief/peak/boss beats, melee/ranged/
fast/tank/elite pressures, upgrade families and build choices, readable
damage and telegraphs, a multi-phase boss, and a bounded full-session test.
The traceability matrix maps “many waves” and “final boss fight” to reachable
rules, ordinary-input evidence, and both gate verdicts. It records written
visual intentions and references, but generates no GPT concept art yet.

The core build uses Three.js primitives and basic functional placeholders. I0
proves boot, focus, movement, camera, damage, restart, terminal states, and
representative GLB loading. I1 proves several minutes of adaptive combat and
reward choices with readable placeholder feedback. I2 makes the full wave and
multi-phase boss journey playable, including actual boss defeat or loss and
re-entry, and runs peak-density seeds. QA repairs blockers first. Two
maker-independent contexts then play the fixed candidate and a demanding core
judge checks the loop, challenge, choices, pacing, readability, and prompt
fidelity. Core graybox visuals are judged for function and legibility, not final
art polish. Any block enters the durable judge/fix/QA/play/re-judge cycle.

After core acceptance, the mechanics/control/collision/camera/timing baseline
is frozen. GPT generation produces inspected hero, enemy, boss, environment,
prop, palette/material, and useful-view references. Blender jobs create the
approved representative set, then the full production cast and effects. Each
job has source/render/export/GLB evidence and a `GLTFLoader` integration check.
The integration candidate checks boss telegraphs, hitboxes, animation timing,
camera occlusion, silhouettes at peak density, VFX/UI/audio, and disposal.

The final gate requires two independent full sessions, complete boot/entry/
combat/wave/upgrade/boss/win-loss/restart/re-entry capture coverage, all
production manifests, static-menu readiness, and three-run callback/Chrome
frame cells for representative play, peak wave, heaviest boss effects, and the
full adaptive session. It judges looks, play, and original-prompt adherence
together. An attractive boss with hollow upgrades or an unreadable peak wave
blocks. Final findings repeat the same evidence-backed quality cycle until the
candidate passes or a real external/budget boundary returns the best revision
and resumable ledger.

## Implementation acceptance for the future rebuild

The future implementation is complete when the package has one public entry
and the private structure above; all literal private names resolve inside its
package scope; and a scratch run journals deep parallel research, detailed
core concept and testable fun hypotheses, traceability, placeholder playable
increments, separate QA/adaptive play/independent core judgment, accepted
core baseline, inspected GPT concept art, post-core Blender production,
integration QA, separate whole-game evidence, demanding repeated quality
cycles, and outside close. It must cover missing-tool/image capability,
absent authority, Blender failure, unplayable host, unqualified/lost
performance trace, evidence contradiction, gameplay-altering art, stagnation,
redesign, and genuine repair exhaustion with closed evidence and resume state.
Validators check identities and shapes rather than sentences; target
dependencies remain in the target lockfile; no private workflow recursively
cycles; and the repository's full required gate passes at the implementation
commit.

## Compact primary-source list

Internal owners: [custom workflow authoring](../docs/custom-workflow-authoring.md),
[standard authoring](../docs/standard-authoring.md),
[standard contract](../contracts/standard.md),
[composition](../rules/composition.md), [vocabulary](../docs/vocabulary.md),
[architecture](../ARCHITECTURE.md), and [repository checks](../AGENTS.md).

External primary sources: [Blender command-line arguments](https://docs.blender.org/manual/en/5.1/advanced/command_line/arguments.html),
[Blender as a Python module](https://docs.blender.org/api/current/info_advanced_blender_as_bpy.html),
[operator limitations](https://docs.blender.org/api/current/info_gotchas_operators.html),
[BMesh](https://docs.blender.org/api/current/bmesh.html),
[Blender glTF manual](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html),
[Blender 5.1 export API](https://docs.blender.org/api/5.1/bpy.ops.export_scene.html),
[Three.js model loading](https://threejs.org/manual/en/loading-3d-models.html),
[`GLTFLoader`](https://threejs.org/docs/pages/GLTFLoader.html),
[Three.js color management](https://threejs.org/manual/en/color-management.html),
[Three.js renderer guide](https://threejs.org/manual/en/webgpurenderer),
[Three.js disposal](https://threejs.org/manual/en/how-to-dispose-of-objects.html),
[Khronos glTF Validator](https://github.com/KhronosGroup/glTF-Validator),
[Playwright input](https://playwright.dev/docs/input),
[Chrome performance reference](https://developer.chrome.com/docs/devtools/performance/reference),
[CDP Tracing domain](https://chromedevtools.github.io/devtools-protocol/tot/Tracing/),
and [pinned DevTools `FramesHandler`](https://github.com/ChromeDevTools/devtools-frontend/blob/9f9f40ba5bca7e385be30535cdbf01a3a7e5ba44/front_end/models/trace/handlers/FramesHandler.ts).
Claims were checked on 2026-09-05; moving API pages describe current
capability only, while each run pins and probes the versions it invokes.
