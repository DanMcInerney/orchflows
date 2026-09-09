# 3D browser-game composition admission

## Scope and contract

This report records the admission boundary for the `3d-browser-game` package
under the `orch-do` contract and `orch-code` standard. The public workflow is
`3d-browser-game`. Its private package members are the `discovery`,
`playable-increment`, `gameplay-gate`, `blender-asset`, and `final-acceptance`
workflows; the `blender-bpy` applied skill; the five package standards; and
the package-owned references and scripts. The discovery helper deliberately
inherits the surrounding project's `research-acquire` applied skill. Private
members resolve only when the public owner is supplied.

The package code under test is copied byte-for-byte from
`example-workflows/3d-browser-game` into a disposable external Git project
at `.orchflows/workflows/3d-browser-game`. The fixture adds only the existing
project-scoped `.orchflows/skills/research-acquire` item needed by discovery's
literal `--skill` edges. No package source, generic resolver, installer, or
legacy `browser-game` file is edited by this ticket.

The package identity is its `tickets_pins.tree_digest("workflow", package)`
value. The dependency contract asserted by the admission test is Node
`>=24.15.0`, npm `>=11.12.1`, and exact package pins `ajv 8.17.1`,
`ajv-formats 3.0.1`, `gltf-validator 2.0.0-dev.3.10`, and
`playwright-core 1.62.1`, with a committed `package-lock.json`. These are
package-tool identities; a target game's Three.js or other runtime lockfile
remains target-owned.

## Doors observed

`tests/test_3d_browser_game_admission.py` is one disposable-project test. It
drives the existing APIs in this order:

1. `orchflows check` grades the copied ring while untrusted. Static package
   admission is allowed to read the package, and declared tooling is named
   with the trust remedy.
2. `orchflows sync --project` renders the public adapters while untrusted and
   skips dependency installation. After `orchflows trust`, the same sync
   reaches the package's `npm ci` declaration. The npm installer is replaced
   by a controlled recorder, which proves the selected lockfile command and
   lock digest without network access. The generated cache is removed before
   the fixture re-grants trust, so later package identity is the copied source
   identity rather than a generated `node_modules` cache.
3. Project adapters are observed at `.claude/skills/3d-browser-game-workflow`
   and `.agents/skills/3d-browser-game-workflow`. Inventory and `list` expose
   the public workflow only; `discovery`, `blender-game-asset`, and
   `blender-bpy` are absent globally. The same three names resolve inside the
   public owner and their paths are contained by that package.
4. `tickets.py frame-open` records the public package name, whole-tree digest,
   and `SKILL.md` entry. A package edit followed by a fresh trust grant makes
   a child `frame-open` refuse the parent’s stale package digest with the
   existing pinned-assignment message. Restoring the bytes and re-granting
   trust permits the private `discovery` frame, which inherits the public
   owner and digest and records `workflows/discovery/SKILL.md`.
5. A real `do` dispatch stamps the private `blender-game-asset` standard and
   `blender-bpy` skill, records their digests, inherits the package identity,
   establishes an isolated Git worktree, and emits the host's frozen Codex
   `spawn_agent` binding. A scripted child process exits 7 and is landed as
   `failed`; the candidate is retired. `orchflows resume` still lists the open
   root and helper frames, proving that the failure is durable and resumable.
6. A second private `do` child runs a scripted fixture that writes and commits
   `admission-proof.txt`, then lands `complete`. A private-scope `judge`
   dispatch reads its typed Git artifact, writes a scripted review fixture,
   and lands `complete`. Both children carry the inherited package digest;
   the judge carries the private `threejs-browser-game` standard. The helper
   and public frames then close through `frame-close`, and a final `resume`
   reports no open frames.

The child exit-7 process, proof writer, and review writer are explicitly
`fixture/scripted` outcomes. They prove ticket lifecycle, worktree, pin, and
resume doors only. They do not claim that a model played a game, judged fun,
ran Blender, validated a GLB, exercised a browser, or executed every prose
branch. Native Blender/browser and performance evidence stays with its
assigned owners.

## Verification record

The joined candidate carries the applied-skill role required by the real
admission resolver: `example-workflows/3d-browser-game/skills/blender-bpy/SKILL.md`
declares `role: worker`. The admission module was first run against the clean
baseline and failed at that missing key; after the metadata repair, the same
real disposable-project test passed.

```text
baseline scoped admission: exit 1 (1 failure, 8.61s)
candidate scoped admission: exit 0 (1 test, 32.81s)
```

The serial compatibility manifest was regenerated from the candidate after
the admission test and native trace tests were present. The writer completed
with the two new admission restoration seams classified as
`selected-module-boundary`, because both context managers restore their
process state before the module returns:

```text
run_serial_compat.py --write-manifest: exit 0
discovery: 2210 identities; sentinels: 12; mutation owners: 388
```

The repository validator completed with exit 1 on the existing package shape:
it rejects the package's schema files under `references/` and scripts under
`scripts/` as forbidden workflow contents. That validator-owned defect is
reported for the root gate and is outside this seam repair.

The admission test remains lifecycle evidence only: its scripted child exit,
proof writer, and review writer do not claim Blender, browser, GLB, gameplay,
or performance qualification. Root owns the full five-check gate and accepted
source install after this joined seam lands.

## Deliberate limits

No live npm network install, Blender process, headed browser, Three.js game,
GLB validator, actual adaptive play session, or performance qualification was
run here. The npm command is verified through the actual Node sync path but
its installer is a controlled recorder; child outputs are deterministic
scripts. No private package member receives an adapter or a global inventory
name. No second workflow engine or resolver path is introduced.
