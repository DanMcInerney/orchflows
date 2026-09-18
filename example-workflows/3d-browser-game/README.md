# 3D browser game

Build a complete Three.js game from a player fantasy: competing mechanics, a playable core, original Blender assets and independent core/final playtests. The target is a game players can learn, finish and retry within your chosen scope.

## Try it

```text
$3d-browser-game:3d-browser-game
Build a salvage game where valuable cargo changes movement and route choice.
Target desktop keyboard/mouse. Make one escalating mission with original
Blender assets, a clear outcome and quick retry in ./salvage-game. Include
the playable build, editable sources and playtest evidence.
```

Claude Code: `/3d-browser-game:3d-browser-game`. Skills are manual-only by default. Supply devices, controls, session length, assets and constraints; unspecified details are chosen and recorded. Existing games and explicitly bounded phases are supported; partial work is labeled.

## Production

| Stage | Required outcome |
| --- | --- |
| Scope and capabilities | Player promise, release boundary, target conditions and observed tool support |
| Playable core | At least three mechanics compared; complete graybox session and two focused before/after experiments |
| Independent core playtest | Uncoached/adaptive play, alternate tactics, setback/retry and a ready core before final assets |
| Production and integration | Inspected Blender exports joined with completed content, finished player flow, QA and performance evidence |
| Independent final playtest | A different fresh reviewer assesses the exact production candidate before delivery |

The coordinator chooses production staffing, with shared direction and one integration owner. Assets and content may run concurrently on separate files. Each playtest allows one necessary repair pass with affected checks and start–play–outcome–retry, labeled maker verification; no second review follows. Unchanged ready candidates need no rebuild/replay. A remaining `needs change` or `unverified` checkpoint stops dependent production and returns findings plus a next action. Extra rounds require your request.

Delivery includes the game/build, controls and reproducible commands; editable code/`.blend` sources, GLBs and dependencies; design/asset notes, scenarios and inspected captures; measured conditions and independent reports tied to build identities. Missing browser play or target-device measurements remain gaps. Public deployment requires a hosting request.

Use [make-blender-game-assets](skills/make-blender-game-assets/SKILL.md) for assets alone or [playtest-3d-browser-game](skills/playtest-3d-browser-game/SKILL.md) for independent review without repairs. The [main workflow](skills/3d-browser-game/SKILL.md), [test interface](references/test-interface.md) and [evidence contract](references/evidence.md) define the gates.

## Install

From a complete Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example 3d-browser-game
```

Setup preserves existing library copies. Follow core `docs/hosts.md` for registration/installation and start a new session; verify availability by name.

Requires core 0.10.0+, native child delegation, JavaScript/package tools, browser rendering/input tools and Blender with Python/glTF export. Projects declare Three.js, build and optional physics/test dependencies in a lockfile. Setup installs none of these runtimes. Image generation is optional.

See [library context](references/library-context.md), [game guidance](guidance/browser-game.md), [Three.js](references/threejs.md) and [Blender](references/blender.md). [Trial request](trials/request.md) and [acceptance](trials/expected-behavior.md) specify validation; they are not observed results.
