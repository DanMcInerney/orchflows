# Orch Browser Game Workflow Plan

**Status:** execution companion to the vBG-1.0 spec (`browser-game-workflow-spec.md`)
**Frozen:** 2026-08-25 (supersedes the 2026-08-25 3D-scoped draft of this plan)
**Workflow name:** `orch-browser-game`

**Thesis:** one orchflows workflow builds any browser game — 2D, hybrid, or 3D by declared presentation profile, optionally local-multiplayer by declared LM level — as a step-by-step DAG executed at maximum width by existing orchflows machinery. The custom surface is one pack plus a roster of **small, single-owner skills** glued by compositions, and the QA family is designed to run **standalone** against any browser game, with multiple counterparties when the game is multiplayer.

## 1. Orchflows fit — the general rules this plan obeys

- **Small composable skills.** Every custom skill below owns one artifact class and one oracle family; anything wider is a composition. Compositions define chains per stub — no fused skills.
- **Parallelization by construction.** `orch-spec` stamps the root; `orch-decompose` cuts the DAG under the pack's slicing law (atom/edge/sole-owner rules, 300-word tickets); `orch-frontier` runs rolling dispatch — every ready ticket in flight. Edges are cut at artifact-identity granularity so lanes launch the moment their specific inputs are admitted, not when a phase barrier lifts.
- **Existing machinery is not rebuilt:** orch-tdd executes code tickets; orch-draft/orch-edit execute design tickets; orch-critique [sequence: critique, repair] + fresh orch-verify form gates; orch-integrate adjudicates every join; orch-loop runs bounded refinement; orch-fixture freezes canaries; carry-packets move context along `depends_on` edges; ticket `sequence` chains same-role skills in one child.

## 2. The WorldClaw transfer (unchanged, restated in one paragraph)

Adopted: typed plan artifacts drive skills; a global foundation freezes before local enrichment; parallel lanes carry sole-owner write scopes, immutable shared context, and attempt budgets; refinement is a bounded loop with an inspector. Corrected: our foundation is **contracts + rules core + topology + playable greybox** (not just terrain), every lane's oracle is executable (renders and VLM judgment layer on top, never alone), and orchflows supplies the concurrency law WorldClaw's paper leaves unspecified (frontier dispatch, reconciler, integrate-at-join).

## 3. The per-game production DAG

Profile-generic; profile-keyed tickets (asset batteries, world oracles) resolve at decompose time from the declared profile. Widths annotated; under rolling dispatch levels are a planning fiction.

```text
G0  brief ─ envelopes declared: profile, seats/LM, physics ─── width 1
G1  concepts ×3 → judged select ────────────────────────────── width 3 → 1
G2  design views ×6 (parallel) → design-unify ──────────────── width 6 → 1
      pillars+core-loops · rules brief · world brief
      visual direction · controls/seats · audio+a11y
G3  CONTRACT FREEZE ────────────────────────────────────────── width 1
      schemas · action/observation unions · QA target manifest
G4  wide build ─────────────────────────────────────────────── width ~9
      rules-core lane (sequence ×3: state → legality/objectives
        → serialize/replay)          baseline-policies
      renderer adapter (per profile) input adapter + mocks
      world topology + greybox       eval/CI cells
      art anchors                    dom-shell/a11y skeleton
      publisher setup
G5  GREYBOX SLICE — mandatory join = FIRST PLAYABLE ────────── width 1
G6  enrichment fan-out ─────────────────────────────────────── width ~12
      asset-family lanes ×5–8 (asset-gen → asset-gate per item,
        per-asset parallelism inside each lane)
      region/zone assembly lanes ×N (immutable topology,
        bounded patches, one reconciler)
      LM module lane (conditional per level)
      presentation lane (HUD · menus · FTUE funnel)
      feel lane (event-queue juice per verb)
      content/history lane (when applicable)
G7  integrate (= ALPHA when feature manifest closes) ───────── width 1
      → refine ≤3 batches (parallel per disjoint scope)
      → optimize (baseline + ≤2 interventions)  (= BETA when
        asset manifest closes, zero A-class)
G8  gate = the game-qa composition (§5) ────────────────────── width ~9 lanes
      → repair (parallel per scope) → RITE-convergent re-verify
G9  release (web-TRC · two keys · rollback drill = GOLD) ───── width 1
```

**Critical path** (~10 serial steps): brief → select → design-unify → contract-freeze → rules-core → slice → integrate → refine → gate-converge → release. The two deliberate joins buy the width after them: frozen contracts make G4 conflict-free; an admitted playable slice makes G6 enrichment of a truth that no longer moves. Milestones are ledger-decided at the marked nodes (first playable / alpha / beta / gold), never prose.

## 4. The skill roster — small, composable, single-owner

**`orch-browser-game` pack** owns: the slicing law producing §3's shapes; the profile definitions and their oracle/battery keys; the completion-oracle registry per ticket class; the workspace form (worktree + render capture + content-addressed asset store); stamp rules requiring the three envelopes at root admission.

Production skills (each one artifact class, one oracle family):

| Skill | Owns | Oracle | Rides on |
| --- | --- | --- | --- |
| `game-topology` | semantic world graph (grid or navmesh per profile) | reachability/adjacency, collision intent, camera/viewport law | new |
| `game-assemble` | binding admitted assets/regions to topology; reconciler mode for shared changes | seam/placement checks, no unauthorized shared edits | new |
| `asset-gen` | one asset request → provider call → conditioned candidate | candidate exists, style-anchor conformance | new |
| `asset-gate` | validation battery (2D or 3D per profile) + clean re-import + provenance | the spec §6 battery; standalone-usable on any asset set | new |
| `game-release` | two-key packet, publication, alias, rollback drill | remote reconciliation, rehearsed rollback | new |

Everything else is existing skills plus pack content: concepts and design views ride `orch-draft`/`orch-edit` (pillars, one-pagers, core-loop closure lint are pack oracles); all code lanes ride `orch-tdd` with pack oracles (mandated patterns lint: fixed-step loop, command input, event queue); greybox construction is ordinary code tickets gated by `game-topology`'s oracle; `game-concept` exists only if the draft+critique composition proves awkward.

## 5. The QA family — standalone, multi-counterparty, one composition

Design requirement from the spec (BG-QA-005/006): the QA subsystem is **one composition, two entry modes** — the G8 gate inside a build run, and a standalone invocation against any browser game URL or build. Never two implementations. Every lane is itself a small skill, independently invocable, reporting in one A/B/C severity language with explicit evidence ceilings.

| Skill | Lane | Needs from the manifest | Multi-counterparty behavior |
| --- | --- | --- | --- |
| `qa-target` | compile/validate the QA target manifest; discover hooks; decide lane applicability | a URL or build path (minimum) | declares seats and drivers |
| `qa-smoke` | boot matrix, console/network/CSP errors, backend cells, web-TRC subset | target only | — |
| `qa-play` | blind full matches via public UI; FTUE funnel; findings | target + guide + seat config | N drivers per match (scripted-policy / blind-agent / mock-device / human); seats concurrent in a match; matches parallel across seeds; N browser contexts for networked targets |
| `qa-rules` | privileged lane: legality fuzz, invariants, seat conformance, replay hashes, **desync battery** | semantic hooks | per-tick cross-client checksums; cross-context replay; soak |
| `qa-visual` | deterministic captures, environment-keyed regression, readability + juice-checklist evidence | target (+capture scenes if hooked) | per-seat viewports at LM3 |
| `qa-perf` | budgets, long-session soak | target + declared budgets | measured at max declared seats |
| `qa-access` | GAG-basic battery, tiered rubric evidence, photosensitivity pass | target | primary-seat AT guarantee |
| `qa-balance` | self-play matrices, win-rate bands, cost-curve recompute, difficulty curves | policy hook + economy/PvP flags | role swaps, paired seeds, multiple bot skills |
| *(report join)* | one severity-taxonomy report, milestone verdicts, RITE-convergence tracking | all lane outputs | composition glue over `orch-integrate` + `orch-synthesize`, not a new skill |

The `game-qa` composition: `qa-target` → parallel dispatch of applicable lanes (width up to 8) → findings join → verdict report. **Standalone value is immediate:** pointed at an external game it runs the blind-capable lanes, states the evidence ceiling on every verdict, and still exercises multiplayer targets with multiple counterparties (mock devices locally, N browser contexts for networked games). Inside a build run the manifest is rich (all hooks), the privileged lane activates, and the same report feeds `orch-repair` and the milestone ledger. Freshness rule enforced structurally: `qa-play` first-experience sessions run in doc-blind child contexts, single-use.

## 6. Parallelism accounting

- **Widths:** 1 → 3 → 6 → 1 → ~9 → 1 → ~12 → batch → ~9 (QA lanes) → 1. Peak ~12; sustained ~6–9. Within `qa-play`, matches × seeds × seats multiply further under the frontier's concurrency cap.
- **Where not to parallelize:** rules core stays one `sequence` lane; the reconciler is deliberately serial for shared topology; RITE repair batches serialize against fresh sessions (the convergence measurement is the point); publication is serial by authority design.
- **Failure containment:** a failed lane spawns a bounded repair ticket and stalls only descendants; the frontier keeps everything else moving. QA lanes are verdict-independent by law, so one lane's failure never blocks another lane's evidence.

## 7. Factory build plan

`orch-build` admission for every item; two parallel tracks after F1 — and the QA track ships standalone value before the factory builds its first game.

| Item | Depends on | Exit |
| --- | --- | --- |
| F1 `orch-browser-game` pack + contract schemas (incl. QA target manifest, findings taxonomy, milestone ledger, profile definitions) | vBG-1.0 spec | pack admission lint; dry-run decompose of a toy brief yields §3's shape |
| F2a production skills ×5 (parallel): `game-topology`, `game-assemble`, `asset-gen`, `asset-gate`, `game-release` | F1 | admission tests incl. deliberately-failing oracle fixtures |
| F2b QA skills ×8 (parallel with F2a and each other) + `game-qa` composition | F1 | standalone run against one never-before-seen external browser game returns an honest, ceiling-labeled report |
| F3 oracle batteries (2D + 3D asset, patterns lint, web-TRC v1, GAG-basic, feel/FTUE checks, desync battery) | F1 | each battery rejects its seeded-defect fixture and passes its clean fixture |
| F4 compositions + frontier dry run | F1–F3 | toy brief runs G0→G5 with no manual routing |
| F5 dogfood: one real LM0 game to first-playable, then through the full gate (recommended first: a small `2d` or `hybrid` tactics game — the evidence says agents succeed far more in 2D, so the *workflow* is proven before difficulty compounds) | F4 | gold-milestone machinery green; `orch-fixture` canary frozen |
| F6 second dogfood at `3d` profile; then bake-offs (3D trio; optional 2D Phaser/Pixi) | F5 | 3D battery + navmesh oracles proven; signed ADRs |

## 8. Boundary

The vBG-1.0 spec remains the law; this plan only arranges its obligations in time and width. Where they disagree, the spec wins.
