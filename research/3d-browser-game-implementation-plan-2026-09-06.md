# `/3d-browser-game` implementation plan

This plan turns the approved [browser-game workflow specification](browser-game-workflow-spec-2026-09-05.md) into one canonical T3 package whose only public name is `3d-browser-game`. Implement from root commit `514520217b3d6a13095b36003f2b13455092e73e`, which contains the validated package-scope prerequisite from `633ad428364ba994e306616eda91a27f7d58091e`. The public workflow accepts `brief` and git-backed `workspace`; the brief plus explicit amendments remains product authority. The package digest, target commit, tool identities, and evidence digests freeze every handoff.

## Frozen package surface

All paths are below `example-workflows/3d-browser-game/`:

| Owner | Exact paths |
| --- | --- |
| Workflow/contracts | `SKILL.md`; `workflows/{discovery,playable-increment,gameplay-gate,blender-asset,final-acceptance}/SKILL.md`; `standards/{browser-game-3d-asset,blender-game-asset,threejs-browser-game,browser-game-interface,browser-game-playtest}/STANDARD.md`; `references/{run-record,traceability,evidence-index,gate-verdict}.schema.json`; `references/{core-rubric,final-rubric}.md` |
| Blender boundary | `skills/blender-bpy/SKILL.md`; `scripts/{capability_probe,blender_job_runner,blender_asset_job}.py`; `references/{blender-job,asset-manifest}.schema.json`; `references/blender-probe-job.json` |
| Play/evidence/performance | `scripts/{browser_harness,performance_collect,trace_frames,validate_evidence,outside_probe}.mjs`; `references/{play-session,capture-matrix,performance-cell}.schema.json`; `references/performance-qualification/{static-idle,continuous-animation,deliberate-stall,canvas-stall-other-layer}.json` |
| Integration/admission | `package.json`, `package-lock.json`, `tools.txt`, package retirement and repository manifest changes named below |

The five private workflow names and five private standard names above are literal call-site names. `blender-bpy` is the sole private applied skill. No helper calls another public workflow, and no quality-cycle helper calls itself. Workflow prose owns discovery → I0/I1/I2 → core gate → concept art/Blender → integration → final gate → outside close. Standards contain only domain judgment: 3D asset evidence, its Blender tightening, Three.js code quality, rendered interface quality, and playtest evidence respectively. They use the current free-form standard contract; no `Lens` headings or role fields are added merely for old validators.

## Shared machine contracts

Every stored JSON document is UTF-8, schema-versioned, closed to unknown fields, and written atomically. Its header is `schema_version`, `kind`, `id`, `artifact_commit`, `created_at`, `producer`, `inputs` (named SHA-256 identities), `environment`, `status`, `gaps`, and `invalidates`. IDs are never reused. Hashes cover final bytes. A validator error names JSON Pointer, expected shape, and observed value. Scripts emit one result object on stdout, diagnostics on stderr, and use exit codes `0` pass, `2` invalid input, `3` capability/unverified, `4` evidence or threshold failure, and `5` timeout/process loss.

`run-record` binds the brief/amendments, workspace baseline, package digest, exact tools, decisions, freezes, increments, jobs, sessions, captures, cells, verdicts, complaints, and resume cursor. `traceability` rows bind each prompt promise to requirement, owner, normal-input path, evidence IDs, both verdicts, and invalidation trigger. `evidence-index` lists typed relative paths and hashes; it may reference only the same artifact commit and declared ancestors. `gate-verdict` contains gate (`core` or `final`), fixed inputs, hard-gate results, 0–4 scored dimensions, strengths, complaint IDs/seams, contrary evidence, confidence, disposition (`pass|fix|redesign|unverified`), and resume state. Only `validate_evidence.mjs` may promote a gate-qualified index; prose judgments remain in rubric and standard files.

The native Blender interface is:

```text
<workflow-python> scripts/blender_job_runner.py --job <job.json> --out <job-dir>
<BLENDER_EXE> --background --factory-startup --python-exit-code 23 --python <package>/scripts/blender_asset_job.py -- <job-dir>/job.json
node scripts/validate_evidence.mjs asset --manifest <asset-manifest.json>
```

`blender-job` fixes job ID, mode (`generate|edit|render|export`), source/input hashes, seed, units/axes/pivot, allowlists, budgets, cameras, render/export settings, and expected outputs. One fresh Blender process and directory serve one job. The runner owns an explicit wall timeout and process-tree termination. It promotes from a temporary directory only after exit 0, echoed job/input digest, contained new nonempty outputs, structural inspection and preview coverage, hashes, zero-error pinned Khronos validation, and the target's pinned production `GLTFLoader` scale/material/animation/collider probe. Failure preserves stdout, stderr, job, and partial-output inventory but promotes nothing. `.blend` remains source; `.glb` plus `asset-manifest` is runtime delivery.

Adaptive play uses one reusable JSON-lines process, with no MCP dependency:

```text
node scripts/browser_harness.mjs --config <harness.json>
```

stdin commands are `observe`, `key`, `pointer`, `wait`, `capture`, and `stop`; each stdout reply carries sequence, monotonic and wall time, screenshot/hash where applicable, visible DOM facts, a compact read-only game snapshot, console/network deltas, and status. The harness launches the production server and pinned browser, focuses the canvas, uses ordinary Playwright keyboard/pointer APIs, and waits on the normal clock. It never calls game mutation methods. `actual play` requires interleaved observation and later input adapted by a maker-independent player; a fixed command list is labeled `scripted input`, and fake time/state mutation is `simulated`. `play-session` records the immutable command/reply transcript and classification, so collectors cannot fabricate provenance.

Performance runs as:

```text
node scripts/performance_collect.mjs --cell <cell.json> --out <cell-dir>
node scripts/validate_evidence.mjs performance --cell <cell-result.json>
node scripts/validate_evidence.mjs gate --gate <core|final> --index <evidence-index.json>
node scripts/outside_probe.mjs --index <evidence-index.json> --workspace <joined-workspace>
```

The collector records rAF callbacks and a padded foreground CDP `ReturnAsStream` trace, completion metadata, markers, and environment. `trace_frames.mjs` is identified by package digest and implements the pinned FramesHandler event model. Qualification must pass the four fixtures: static reporting, continuous canvas attribution, deliberate-stall rejection, and rejection when callbacks or another layer continue while canvas draws stall. Any data loss, clock/join mismatch, parser mismatch, ambiguous canvas attribution, missing window, or unparsed event yields `performance: unverified`. For animation, `N>0`, clean game-canvas `C/T>=59`, unique dropped-or-partial `D/N<=1%`, callbacks/T ≥59, ≥99% callback intervals ≤18.33 ms, and no unexplained stall >100 ms; three warm 60-second runs use the identical cell. Static surfaces report counts without an FPS claim.

## Parallel implementation and join

1. The workflow/contracts owner writes only its table row plus `tests/test_3d_browser_game_workflow.py` and `tests/test_3d_browser_game_contracts.py`. Tests check public/private literal resolution, acyclic calls, stage ordering, schema closure, authority/invalidation, gate dispositions, and that judging criteria stay in standards/rubrics rather than workflow ordering.
2. The Blender owner writes only its row plus `tests/test_3d_browser_game_blender.py`. Unit fixtures cover malformed/escaping jobs, timeout, stale/partial output, digest mismatch, and promotion. A host probe uses Blender 5.2.1 LTS build `9e2066aef7ef` from its discovered absolute path and labels only the observed render/export/GLB facts.
3. The play/evidence owner writes only its row plus `tests/test_3d_browser_game_play.py`. Tests exercise JSONL focus/input/observe provenance, label separation, evidence conflicts and missing cells, all four performance qualifications, overlapping dropped/partial counting, and fail-closed loss/attribution. Chrome `152.0.7977.76` and available Playwright Chromium are capability observations, not proof of actual play or performance.
4. After all three return, the integration owner alone writes `package.json`, `package-lock.json`, `tools.txt`, `tests/test_3d_browser_game_admission.py`, and `tests/serial_compat_manifest.json`. Initial exact Node pins are `playwright-core@1.62.1`, `ajv@8.17.1`, and `gltf-validator@2.0.0-dev.3.10`; the lockfile is authoritative, and no Python requirements are needed beyond Blender's own `bpy`. Game Three.js/decoder/physics versions remain in each target workspace lockfile. Per-run capability records pin absolute Blender/browser paths, versions/builds, backend, OS/driver, and hashes; package code never hard-codes this host's path.

The integration owner removes the replaced `example-workflows/browser-game/` public entry, its four obsolete shared `example-workflows/references/browser-game-*` files, and superseded `tests/test_browser_game_*.py` only after equivalent new tests exist. No alias remains, because the requirement is one public entry. No global registry or installer edit is planned: prerequisite evidence shows gallery discovery and adapter generation already accept `3d-browser-game`; a failing admission check is required before widening that surface.

Admission copies the package into a disposable project ring, runs `orchflows check`, trust/sync, and a scratch miniature production-build run that opens every private helper, resolves all literal names, records package/standard digests, exercises a real Blender probe, ordinary-input browser transcript, qualified fixture traces, both validator paths, failure/resume cases, and outside close. Fixture or scripted results keep those labels and cannot pass play-quality gates. The integration gate then runs affected tests and the repository's full `tools/run_required.py --no-cache` at the joined commit. The accepted record includes failing/can-fail readings, passing readings, package digest, commit, uncovered host claims, and `gaps: []` only if all real gate requirements were observed.

Cut log: no settled technical choice was re-researched; no generic orchestration engine, old-workflow compatibility layer, target-game dependency, or unrelated migration entered scope. The only baseline deviation is the approved public rename from `browser-game` to `3d-browser-game`.
