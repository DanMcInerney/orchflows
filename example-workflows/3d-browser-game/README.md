# 3D browser game

**Make a game worth pressing Restart for.**

Give this workflow a player fantasy. It develops competing mechanics, builds a playable Three.js loop, tests the decisions, produces original Blender assets and independently reviews core and final play. The aim is a complete game at your chosen scope: something a player can learn, finish and want another attempt at.

Think cargo that changes how you steer. A shortcut that becomes dangerous when you're winning. A puzzle whose rules reveal a second solution. This workflow puts those decisions at the center of production, then builds the art and progression around them.

## Try it

After installation, paste into Codex:

```text
$3d-browser-game:3d-browser-game
Build a salvage game where valuable cargo changes movement and the safest
escape route. Target desktop browsers with keyboard and mouse controls.
Make one complete escalating mission with original Blender assets, a clear
outcome and quick retry. Work in ./salvage-game and include the playable
build, editable sources and playtest evidence.
```

In Claude Code, use `/3d-browser-game:3d-browser-game` with the same brief. All skills in this library are manual-only by default.

Bring a new idea or an existing game. Specify devices, controls, session length, assets and constraints that matter; the workflow chooses and records unspecified details. You can also request a bounded production phase, which uses only the roles that phase reaches and is delivered as partial work.

## How an idea becomes a game

The [main workflow](skills/3d-browser-game/SKILL.md) follows five stages, with required evidence before dependent work advances:

| Stage | What happens |
| --- | --- |
| Establish scope and capabilities · 1 | Set the player promise, release boundary, target conditions and observed tool/testing capabilities. |
| Produce the playable core · 2 | Compare at least three mechanics, choose the rules, build a testable graybox session and record two focused mechanics experiments. |
| Independently review the core · 3 | A fresh playtester attempts uncoached play, alternate tactics, setbacks and retry. Establish a ready core before final asset production. |
| Produce and integrate the game · 4 | Direct and produce Blender assets, develop content, join their completed results, finish the player experience and gather QA/runtime/performance evidence. |
| Independently review and deliver · 5 | A different fresh playtester reviews the exact production candidate; handle any permitted repair and deliver the checked result. |

The orchestrator chooses production assignments; a full run requires both independent playtests. Shared creative direction and integration ownership keep the game coherent. Blender production and game content can run concurrently on separate files. Guidance gives makers and reviewers the same applicable quality criteria, with production methods kept alongside them and in the references.

Each independent review permits at most one necessary repair pass and no further review. A repair includes affected checks and the main start–play–outcome–retry session, labeled as maker verification. An unchanged ready candidate keeps its evidence without another rebuild or replay. A blocked core stops before final asset production. If a checkpoint remains `needs change` or `unverified`, the workflow returns the best runnable state, findings and a precise next action. Extra review/repair rounds require your request.

## What you get

- A runnable game and production build, with controls and reproducible install, build and test commands.
- Editable game code, `.blend` sources, GLB exports, dependent assets and re-export instructions.
- Design and asset notes, scenario entry points, inspected captures and measured performance under stated conditions.
- Independent playtest reports tied to exact builds, repair records and an explicit `ready`, `needs change` or `unverified` conclusion.

Playtests start with public player instructions so the reviewer has to discover the game through play. The [test interface](references/test-interface.md) makes scenarios reproducible; the [evidence contract](references/evidence.md) keeps ordinary play, automated checks and maker verification distinguishable. Missing browser play or target-device measurements stay visible as gaps. Public deployment follows a separate hosting request.

Need only one part? [make-blender-game-assets](skills/make-blender-game-assets/SKILL.md) produces editable assets and inspected runtime exports. [playtest-3d-browser-game](skills/playtest-3d-browser-game/SKILL.md) independently reviews an existing build, with no repairs.

## Install and requirements

From a complete orchflows core checkout, with Python 3.11+:

```sh
python scripts/orchflows.py setup --example 3d-browser-game
```

Setup copies the example into your orchflows home and preserves an existing library copy. Follow core `docs/hosts.md` to register and install `3d-browser-game@orchflows-home`, then start a new session. Setup alone does not register the skills.

Requires orchflows 0.10.0+, native child delegation, a JavaScript runtime/package manager, a browser with rendering and input tools, and Blender with its Python API and glTF exporter. Projects declare Three.js, build and optional physics/test dependencies in a lockfile. Setup installs no game engine, browser driver or Blender binary. Image generation is optional; sketches and Blender studies can supply art direction.

For the contracts behind production, see [library context](references/library-context.md), [Three.js](references/threejs.md), [Blender](references/blender.md) and [game guidance](guidance/browser-game.md). The [trial request](trials/request.md) and [expected behavior](trials/expected-behavior.md) describe validation to run; they are not observed results.
