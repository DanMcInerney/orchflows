# 3D browser game

Build a complete Three.js browser game with a tested central mechanic, deliberate progression, original Blender assets and independent playtesting. The workflow spends time on decisions, feel and replay value before expanding content. A short, coherent game is a valid scope; an attractive scene with movement is not a finished game.

## Production sequence

The [workflow](skills/3d-browser-game/SKILL.md) gives each of its 20 steps an output and a condition for advancing: brief, capabilities, mechanics brainstorm, concept selection, experiment plan, testable architecture, controls and camera, graybox loop, mechanics experiments, independent core playtest, core repairs, art direction, Blender production, content and progression, asset integration, presentation, regression QA, performance, independent final playtest, and delivery.

One game uses four children, excluding the caller: one game maker continued across phases, one core playtester, one Blender maker, and one final playtester. Both playtesters are fresh independent reviewers. The caller delegates and joins all children; the Blender maker and game maker can work concurrently on agreed, separate files. Each review allows at most one necessary repair pass and no additional review. An unchanged ready candidate keeps its existing evidence without rebuilding or replay. A blocked core stops before final asset production. Individual asset or playtest skills each use one child.

## Ownership

| Location | Purpose |
| --- | --- |
| [Main workflow](skills/3d-browser-game/SKILL.md) | Ordering, assignments, checkpoints and repair bounds |
| [Blender asset skill](skills/make-blender-game-assets/SKILL.md) | One asset maker, source through runtime handoff |
| [Playtest skill](skills/playtest-3d-browser-game/SKILL.md) | One independent reviewer playing an exact build |
| `guidance/` | Game design, Three.js, Blender and playtest quality criteria |
| [Library context](references/library-context.md) | Dependencies and guidance selection |
| [Test interface](references/test-interface.md) | How an agent observes, controls and reproduces a game |
| [Evidence](references/evidence.md) | Small records linking claims to builds and observed sessions |
| [Three.js](references/threejs.md), [Blender](references/blender.md) | Tool-specific implementation and asset handoff knowledge |
| `trials/` | Ordinary trial requests and expected behavior; run outputs live elsewhere |

## Install and use

Requires orchflows-light 0.6.2+, native child delegation, a JavaScript runtime/package manager, a browser with rendering and input tools, and Blender with its Python API and glTF exporter. Projects declare their own Three.js, build and optional physics/test dependencies in a lockfile. No game engine, browser driver or Blender binary is bundled or installed by setup. Image generation is optional; authored reference boards and Blender studies can supply art direction.

From a complete core checkout, run `python scripts/orchflows.py setup --example 3d-browser-game`. This copies the library once and preserves existing destinations. Follow core `docs/hosts.md` to register and install `3d-browser-game@orchflows-home`, then start a new session. Adding files to this checkout alone does not register the skills.

Invoke `3d-browser-game:3d-browser-game` with a game brief, workspace and any target devices, controls, session length, existing assets or constraints. Unspecified choices are made and recorded. For example: "Build a salvage game where carrying valuable cargo changes movement and the safest escape route. Desktop browser, one complete escalating mission, original Blender assets."

Output includes editable game and Blender sources, production build, playtest controls and scenarios, reproducible commands, measured evidence, review findings and unresolved gaps. External deployment follows the caller's hosting request and available hosting skill; it is not an automatic production step.
