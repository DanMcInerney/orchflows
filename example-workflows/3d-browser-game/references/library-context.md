# Library context

Require core `orchflows` (`orchflows:orch-review`); apply its `docs/architecture.md` and `docs/hosts.md`. Include this library and caller-supplied libraries in order.

| Work | Guidance |
| --- | --- |
| Design | `browser-game`; `writing` for player/design copy |
| Implementation | `code`, `browser-game.threejs` |
| Art | `visual-design`, `browser-game.blender` |
| QA/review | `browser-game.playtesting`; core review also gets Three.js, final review all three game specializations and relevant core domains |

Standalone leaves select their specialization and relevant core domains.

Suggested new-project directories are `game/`, `assets/source/`, `notes/` and `evidence/`, not a required schema. Give asset production its own directory and game integration one code owner. Concurrent workers need separate tabs/capture locations; serialize interactive tools the host cannot isolate.

Required Blender assets and actual play cannot be replaced by mocks. Project-specific harnesses belong to the project.
