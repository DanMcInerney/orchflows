# 3D browser game workflow rebuild

Authoring record, not workflow instructions. Candidate: `example-workflows/3d-browser-game/` in this checkout. The main workflow owns production order; domain guidance owns quality criteria; references own tool knowledge and handoff contracts.

## Legacy investigation

Read the archived installed `3d-browser-game` and its source in the old Orchflows repository at [803ef3f832a700f38bfe018d824646a106251e38](https://github.com/DanMcInerney/orchflows/tree/803ef3f832a700f38bfe018d824646a106251e38/example-workflows/3d-browser-game). One independent investigator inspected the subworkflows, standards, earlier specifications and repair history; the author inspected the entrypoint from both archive and Git.

Preserved: prove ordinary input and a complete graybox loop before broad art production; distinguish scripted QA from adaptive play; inspect editable Blender source and exported assets through the production loader; recheck gameplay after art changes; tie findings to actual builds.

Rebuilt: explicit mechanics alternatives, decision-based concept selection, feel tuning, two observed mechanics experiments, progression/content planning, first-class agent test access, practical Three.js engineering, Blender art craft and concrete uncoached/adaptive review sessions.

Omitted: ticket frames, schema-heavy acceptance machinery, repeated judges, native-frame attribution scripts and inherited survivor-game/boss assumptions. The old universal frame-rate floor originated in a specific request; the new workflow derives budgets from the target. No legacy runtime or scripts were copied.

## Candidate and checks

The library has three skills, four guidance domains, five shared references and a bounded trial brief. A full game uses one continued game maker, one Blender maker and two independent playtesters: four children plus the caller. The main skill has 20 numbered production steps, with at most one necessary repair pass after each independent review and explicit stop conditions.

Static checks passed:

- Plugin validator and all three skill validators. Validators used an ephemeral `uv` environment with PyYAML; the core runtime was not modified.
- `python -m unittest discover -s tests`: 65 tests, one existing skip. An initial failed check caught a root README link to an example omitted from shipped core; the link was corrected and the suite rerun successfully.
- Isolated home setup copied all 18 package files exactly, resolved all three skills, returned ready from `doctor`, and preserved the library on setup rerun. All 22 local Markdown links resolved within the installed library and manifest identities agreed. This used a disposable home and skipped host configuration.
- `git diff --check` passed. The new library has not been registered or installed into the user's active host.

Static checks cannot establish game quality, browser compatibility or end-to-end production behavior. The completed behavioral trial and final author verification are recorded below.

## Trial input evolution

The trial coordinator recorded a 17-file input hash manifest, excluding the expected-behavior file it had not read. The author later changed four files while the trial was running:

| File | Change and scope |
| --- | --- |
| Package README | Raised the declared minimum core from 0.6.0 to the tested 0.6.2; no game-production behavior changed. |
| Blender reference | Added newer action-slot/export documentation. Full asset production was not reached. |
| Library context | Clarified the specializations received by core/final reviewers and concurrent browser-tab/capture ownership. The coordinator and core reviewer reused originally resolved absolute guidance paths; neither re-read this context. Their selected core review paths already included the Three.js specialization. |
| Main skill | Added explicit declared browser/device/input-matrix coverage at step 17, which this bounded trial did not reach. |

The trial therefore supports observed behavior under its recorded inputs and read history, not a claim that every line of the final candidate was executed. Candidate files were frozen during the final workflow review; subsequent review repairs are recorded separately below.

## Bounded behavioral trial

An independent coordinator ran the library's ordinary salvage-courier brief in an unrelated empty project, using declared dependencies and no borrowed game scaffold. The author bounded the run at steps 1–11 during implementation. It used two workflow children: the original game maker and a fresh core reviewer. See the [complete trial record](C:/Users/danhm/tmp/orchflows-game-trial-20260912/trial-record.md), [independent core report](C:/Users/danhm/tmp/orchflows-game-trial-20260912/notes/core-review.md) and [no-repair closeout](C:/Users/danhm/tmp/orchflows-game-trial-20260912/notes/core-repair.md).

Observed results:

- Blender 5.2.1 source/export and a GLB loaded in Three.js r186 through the host browser; real render/input, pause and view controls were inspected. This was a disposable capability probe, not final asset craft.
- Three mechanics alternatives and pre-implementation experiment predictions, followed by an original complete graybox mission with light and heavy cargo, exposed and sheltered routes, delivery and replay.
- Same-scenario braking comparison: changing response 5.0 to 1.7 increased travel after 120 ticks from 0.5075 to 1.5136 meters. Gust comparison: changing acceleration 0.8 to 1.7 changed survival on the exposed span into a tow at tick 85 with 85% cargo condition. Captures and state records were retained and repeated on the frozen identity.
- The independent reviewer played two ordinary sessions before reading design/maker notes: a clean sheltered heavy return, then a risky failure followed by a changed strategy and recovery. It observed both routes, delivery and replay, reproduced the seeded tow twice, and checked manual time/reset behavior. Six rule tests passed. It reported core ready with no material findings on `core-59334af116ef`.
- All 12 source entries and three built entries remained unchanged during core review/closeout. Early working captures with stale labels were disclosed and not promoted to frozen-build proof. Trial-owned servers were verified and stopped; source, evidence and restart commands were retained.

The unconditional repair-pass text initially prompted another full replay despite an unchanged, passing core. That attempted replay found the browser unavailable and produced no new gameplay observation. The author intervened to close with existing evidence and no repairs. This observed instruction problem informed the final repair below; it is not a gameplay regression or a completed additional test.

Limits: steps 12–20, full four-child composition, final Blender asset quality, production integration/final acceptance, failed-core stopping and actual defect repair remain unexercised. Precise held-key timing, deliberate blur/resize, other seeds, graphics/asset failure and target performance/backend remain unverified. The successful core is not a complete delivery against the original final-art brief, proof of human enjoyment, or qualification of the entire workflow.

## Independent review and final repair

One fresh reviewer inspected all package files, repository contracts, completed trial records and selected captures without editing or replaying the game. Its [pre-repair report](C:/Users/danhm/tmp/orchflows-game-validation-20260912/workflow-review.md) identified three findings. The author made one repair pass:

| Finding | Repair and verification |
| --- | --- |
| WF-01: unconditional repair/retest | Main coordination, steps 11/20, README and trial expectations now skip repair/rebuild/replay for an unchanged ready candidate. Necessary repairs retain the one-pass upper bound and affected checks. The trial's author-directed no-repair closeout exercised this decision; the revised full workflow was not rerun. |
| WF-02: step 13 assigned to a child forbidden to delegate | The caller now explicitly owns Blender dispatch and joining. The game maker receives step 12, step 14, then steps 15–18 after the join. Static assignment tracing confirms all children have production-only work. This later-stage handoff remains behaviorally untested. |
| WF-03: retired Three.js manual links | Replaced both `/manual/en/` links with current `/manual/pages/` paths. Direct requests returned HTTP 200 and the expected page titles. |

After repairs, plugin/changed-skill validation, exact isolated installation, three-skill resolution, doctor, preservation on setup rerun, all 22 local links and whitespace checks passed. The core's earlier 65-test run remains applicable; no core code changed. No second independent review was added.

Final main skill SHA-256: `437C76E489C7BB6F51911F1F5B90607AE93A67F5025D24E58E6D501B682DD6EE`. Final Three.js reference SHA-256: `5B8958636D8CA3BD355A203A594EFED155FE0DE1A3175E2B8BE975156FE5914A`. These identify the author-verified post-review files, distinct from the pre-repair candidate recorded by the reviewer.

## Full Nightbind dogfood run

The caller subsequently requested a complete game using this example workflow: a twelve-wave horde survival run with actual enemy recruitment, earned evolutions around waves 5 and 10, varied combat roles and a final boss. The project is [Nightbind](../example-workflows/nightbind/README.md); its [running dogfood record](../example-workflows/nightbind/notes/dogfood.md) distinguishes observed behavior, workflow friction and remaining work. This extends the earlier bounded trial; it does not retroactively change that trial's scope or evidence.

The core checkpoint passed independent ordinary play on `core-220cfa39951c`, with capture decisions, wave-9 pressure, earned Worldcoil relief, boss victory, an ordinary failure and clean retries. No repair or redundant replay was required. Only initial onboarding was uncoached: the first review read private notes before the full outcome. That observed ambiguity prompted a clarification in the playtest leaf: withhold private notes until the first ordinary outcome or observed blocker, reuse the completed run and disclose any early access. A second clarification explicitly preserves raw frame intervals before simulation-time clamping. The hashes above identify the earlier authoring closeout, not these later changes.

The caller-owned Blender dispatch and concurrent code phase have now been exercised. Representative runtime inspection exposed and corrected an exported socket rotation before expansion. The completed asset handoff contains 22 validated GLBs, 24 editable Blender files and 15 portraits. All exports passed Khronos validation without errors or warnings, loaded through the game's shared loader and reproduced byte-for-byte from saved sources. Four-facing game-camera views exposed shape problems that source beauty renders alone missed. The caller independently checked all 70 delivered inventory entries against file hashes and sizes.

The joined game reached steps 15–18 ready on unchanged `release-c09f13cac8e9`, with a separate `qa-c09f13cac8e9` from the same source digest. The caller operated the supported browser while the maker inspected evidence and verified the frozen files. An ordinary first loss informed changed acquisition timing and movement. The next run earned Dusk at wave 5 and Eclipse at wave 10, reached 240 active enemies, defeated the Bellkeeper, and retried cleanly. The report preserves Dusk's gradual first relief, strong health recovery during disciplined movement and Eclipse's shorter boss fight rather than claiming every composition behaves identically.

Actual ordinary rendering on Intel/D3D11 at 1280×720 met the stated target: the busy 150–240-hostile section had p95 16.9ms and maximum 18.9ms across 1,160 active frames. Public pauses divide the live segments. The first full-history export hit the browser tool's return limit; bounded raw rows and read-only aggregates recovered the measurement, while truncated artifacts remain explicitly invalid. Alternate integrated forms, full-roster release/capture, reduced-motion combat, repeated retries and missing-asset recovery passed targeted checks. Other physical devices, deliberate blur/context loss, audible quality and fully cold startup remain unverified. See the [caller production report](../example-workflows/nightbind/notes/caller-production-play.md), [maker QA](../example-workflows/nightbind/notes/production-qa.md) and [performance report](../example-workflows/nightbind/notes/performance.md).

All 97 fingerprinted source files, 41 release outputs and 43 assisted-test outputs matched the frozen manifests. The caller dispatched the fourth fresh child for final independent play on this joined candidate. It will also assess the two small instruction clarifications after its first public-only game outcome, within the already declared review rather than adding another agent. Final acceptance and delivery remain pending at this entry.

At final-review dispatch, the main skill remains `437C76E489C7BB6F51911F1F5B90607AE93A67F5025D24E58E6D501B682DD6EE`. The clarified playtest leaf is `6E53A906E12ECD99347379DD1D7C110769B93CD847AFCCE34214FC55682E813E`; the clarified Three.js reference is `741414CD7A34E8E2491E8A15D2EBE85C62C904CABB04602E83714009D351E978`. These distinguish the exercised production instructions from the earlier authoring closeout hashes.

The final reviewer subsequently recorded its first ordinary outcome: a wave-four loss, 174 enemies defeated, no evolution, and a roster including a duplicate Emberling. It changed an intended route when the reachable capture pool differed, then experienced poison/destination-dwell damage. It explicitly confirmed that no private game notes, source or diagnostic snapshots had been read before the outcome. That exercises the clarified boundary in observed use. Its later representative retry and diagnostic work are informed; final judgment remains pending.

## Completed production review and delivery

The fourth child's [final independent review](../example-workflows/nightbind/notes/final-review.md) is **READY for the requested local desktop game** on unchanged `release-c09f13cac8e9`. Its informed ordinary retry earned Pyre at wave 5 and Solar at wave 10, won against the Bellkeeper at 266.95 seconds with seven captures and exactly two evolutions, and retried cleanly. A stationary challenge before ascension lost 46 health in 8.3 seconds; movement recovered. Solar then reduced 177 hostiles to 32 in 4.57 seconds, followed by a quiet interval and renewed boss dodging. The report distinguishes crowd pressure from low-health peril and retains the scheduled spawn reduction as a comparison confound.

Independent targeted checks covered missing/full recipes, actual enemy capture, paused stepping, remaining evolved forms and low-health boss loss/retry. Five saved Blender sources opened with editable hierarchy/materials. Thirteen game tests passed. Independent hashes matched both 97-file source manifests, all 41/43 outputs and 28 frozen handoff documents; release diagnostics isolation passed. The reviewer independently recalculated the caller's heavier ordinary performance slice rather than treating a manual scenario or menu as a benchmark.

No material blocker required repair. Step 20 therefore closes with the same tested source, assets and builds, without another rebuild, replay or reviewer. The [delivery record](../example-workflows/nightbind/notes/delivery.md) was added after review and points to the runnable preview, editable source, commands and evidence. Earlier fingerprinted handoff notes preserve their historical readiness statements. The final reviewer closed its own tabs; the local development, ordinary and assisted servers remain available for the user.

Nonblocking observations remain explicit: late capture demand falls after assembling a planned squad, Solar leaves a quiet wave-eleven interval, and some loss advice is generic. Device/input/audio/cold-start limits remain as recorded. The game was exercised through the full 20-step production flow and all four production roles; actual defect repair and failed-checkpoint stopping remain unexercised branches.

The same final reviewer accepted both narrow instruction clarifications under Orchflows/writing Review, with observed first-play behavior and raw-timing source/evidence support. No additional authoring-review round was added. The existing package validations and 65-test repository run remain applicable: no core code or workflow instructions changed after their latest checks. The library is in `example-workflows/3d-browser-game`; it has not been installed into the active host.
