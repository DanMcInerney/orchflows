# Library context

Apply core `docs/architecture.md`.

Resolve dependencies at the outer entrypoint, including either leaf invoked alone. Use core native skills, supplied package roots or core's `resolve` CLI; cache resolved paths and extend them when composed work introduces a dependency. Use core `docs/hosts.md` for host capabilities and isolation.

Include this library and caller-supplied package roots in supplied order. Select `browser-game` for game design, with `writing` for player/design copy, `code` and `browser-game.threejs` for implementation, `visual-design` and `browser-game.blender` for art, and `browser-game.playtesting` for QA and review. Give reviewers the same applicable quality criteria: core reviewers also receive Three.js guidance; final reviewers receive all three game specializations and relevant core domains. A leaf selects its specialization and relevant core domains when invoked alone.

Pass the original player brief, applicable caller amendments and constraints, workspace, selected guidance, core primitive locations and library root with each assignment. Add phase, owned files, dependencies, current build identity, run commands and relevant records. Reviewers receive the public player instructions separately from design intent and maker findings so they can attempt first play without a walkthrough.

Put code, `.blend`, assets, notes, tools and evidence in the caller's project workspace. Use the existing project layout or `game/`, `assets/source/`, `notes/`, `evidence/` in a new workspace. These are suggested locations, not a required schema. Never write run outputs into the library. For shared workspaces give Blender one asset directory and game maker all integration/code files; freeze the candidate during reviews, or give the reviewer a copy including uncommitted files and a separate server/port. Give concurrent workers their own browser tabs and capture locations. If the host cannot isolate a shared interactive tool, serialize its use while independent file work continues.

Probe actual capabilities before making dependent promises: project install/build, rendered browser input and captures, Blender source/export, image inspection and optional audio playback. A successful version command alone is not a capability test. Follow the host's browser skill and supported tools; a test hook does not authorize bypassing restrictions on page evaluation. When arbitrary evaluation is unavailable, expose the same test operations as a development-only DOM panel and use visible controls. If a capability remains unavailable, continue independent work, record the missing check and stop at the affected checkpoint. Do not silently replace required Blender assets or actual play with mocks.

This package supplies instructions and contracts. Generated project-specific harnesses belong to that project.
