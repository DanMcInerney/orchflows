# Library context

Require core 0.10.0+; apply its `docs/architecture.md` and `docs/hosts.md`. At any entrypoint, resolve core primitives through native skills, supplied roots or core's `resolve` CLI; reuse paths and extend dependencies for new work. Include this library and caller-supplied libraries in order.

| Work | Guidance |
| --- | --- |
| Design | `browser-game`; `writing` for player/design copy |
| Implementation | `code`, `browser-game.threejs` |
| Art | `visual-design`, `browser-game.blender` |
| QA/review | `browser-game.playtesting`; core review also gets Three.js, final review all three game specializations and relevant core domains |

Standalone leaves select their specialization and relevant core domains. Give each assignment the brief, applicable amendments/constraints, workspace, guidance, core/library paths, phase, owned files, dependencies, build identity, commands and relevant records. Separate public player instructions from maker findings/design intent for uncoached review.

Keep outputs in the caller's project; suggested new-project directories are `game/`, `assets/source/`, `notes/` and `evidence/`, not a required schema. Give asset production its own directory and game integration one code owner. Freeze review candidates or copy all inputs, including uncommitted files, to a separate server/port. Concurrent workers need separate tabs/capture locations; serialize interactive tools the host cannot isolate.

Probe actual install/build, rendered input/captures, Blender source/export, image inspection and applicable audio; version commands alone are insufficient. Follow supported browser tools: test hooks do not authorize restricted page evaluation. When evaluation is unavailable, expose equivalent development-only DOM controls. Missing capabilities block affected checkpoints; continue independent work and record gaps. Required Blender assets and actual play cannot be replaced by mocks. Project-specific harnesses belong to the project.
