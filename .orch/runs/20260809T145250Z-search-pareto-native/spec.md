# Code spec: Pareto-native search-fusion acquisition utility

- `run`: `20260809T145250Z-search-pareto-native`
- `supersedes_for_implementation`: `.orch/runs/20260809T103759Z-native-search-fusion/spec.md`, SHA-256 `A1178C700B9CAE3A8390935ADF66C6DB9737AA9F949F7B87CB1C2F2675E22FD3`; that spec remains frozen history.
- `objective`: A project-scoped `search-fusion` acquisition utility exists whose original Python 3.9+ standard-library implementation, exercised through two explicit offline fake adapters, deterministically executes caller-frozen discovery followed by ordinary-lane-selected fetch through stable discovery-hit references, refuses unauthorized or S2-unenforceable routes before I/O, conditionally expands a bounded same-origin S3 site by repeatedly invoking fetch, and emits one canonical run-scoped acquisition-artifact family preserving provenance, bounded content, typed outcomes, warnings, and explicit loss, while ordinary orchflows research retains every selection judgment, finding, confidence decision, contradiction judgment, and synthesis.
- `non_goals`:
  - Importing, installing, executing, vendoring, copying, or delegating to Agent Reach, Last30Days, OpenCLI, GPT Researcher, another external skill, provider SDK, prompt contract, planner, router, ranker, or synthesizer.
  - Shipping a live/network adapter, selecting a provider winner, or certifying provider quality, privacy, availability, latency, price, retention, or regional behavior.
  - Dynamic plugins, entry-point discovery, installer/update ownership, arbitrary module names, executable shell strings, or external-skill subprocesses.
  - Authentication, credentials, opaque sessions, browsers, private data, S4, profile persistence, remote mutations, or any write-capable action.
  - Utility-owned query planning, discovery-result selection, lane cutting, accepted findings, independence judgment, confidence, contradiction resolution, or terminal synthesis.
  - Ranking, RRF, reranking, required-source round robin, clustering, MMR, provider/agreement scores, consensus confidence, or selected/unselected/remainder state.
  - Enrichment, comments/transcripts, CSS/model extraction, provider-generated conclusions, async jobs, polling/checkpoints, retry, fallback, relaxation, escalation, internal engine fan-out, cache, watch, library/history state, or health probes.
  - A public counter or normalized-cost schema. Hard-cap state and the fake call ledger are implementation/test internals; optional provider usage remains opaque.
  - A new custom workflow/composition, recurring monitor, canonical routed entry, T0 contract, pack, kernel, top-level `scripts/`, installer, or managed-instruction-block change.

- `target_repository`: `C:\Users\danhm\.codex\worktrees\07ca\orchflows-public` at commit `7f01ba20adf51a3332adf5ac9d318eca8d333fa9`.
- `standards_owner`:
  - `AGENTS.md` for repository instructions and required checks.
  - `ARCHITECTURE.md` for tiers, ownership, dependency direction, and package-local scripts.
  - `packs/orch-code-pack/references/craft.md` for explicit seams, locality, searchable call sites, tracer shape, and oracle-led design.
  - `packs/orch-code-pack/references/oracles.md` for deterministic checks and the independently judged code-lens gate.
  - `skills/workflows/orch-build/SKILL.md` and `skills/workflows/orch-build/references/scopes.md` for project custom-item admission and host adapters.

- `acceptance`:
  1. The project item is an original native implementation: no runtime import, vendored artifact, copied prompt/configuration, dynamic import/registry, executable shell string, external-skill subprocess, provider SDK, or call edge targets an external agent skill; adapter declarations cannot name arbitrary modules or commands, and all adapter call sites are statically searchable. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_dependency_boundary.py" -v`, with one independently failing seed for each forbidden form. `oracle_class`: `deterministic`.
  2. Static adapter declarations and one pure `authorize_route` path freeze base authority as `public`/`read`/`public_data`/`run_only`, filter required operation, S2 source role, and publication-interval enforcement before stable first-eligible routing, and return `refused` or `no-route` with every elimination reason for unsupported authority, operation, role, freshness, region, or retention. Refusal invokes no adapter; no health, history, probe, reservation, price, quality score, override fallback, or hidden default affects routing. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_router.py" -v`, including reordered declarations, unsupported requirement, all-eliminations, and zero-call wrong-result fixtures. `oracle_class`: `deterministic`.
  3. Discovery and fetch are separate invocations. A discovery manifest carries stable manifest/slice/request identities, one caller-frozen query, required S2 source role, requested publication interval, and hard caps; its artifact emits stable hit IDs. A fetch manifest carries the prior discovery-artifact ID and the ordinary lane's ordered hit-ID choices; unknown, foreign, locator-mismatched, or implicit native-top-result selection fails before fetch. Requested/applied publication intervals and item publication times survive; an empty successful source remains distinguishable from degradation, and stale or unknown-date items remain explicit failures/loss rather than successful evidence. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_pipeline.py" -v`, including two S2 roles, one genuine empty, one degraded route, stale/unknown-date seeds, mismatched hit references, and a runner-auto-selection seed. `oracle_class`: `deterministic`.
  4. `AcquisitionArtifact v1` is the only public result family. It retains stable manifest, slice, request, attempt, item, adapter, upstream, prior-artifact, and hit-reference identities; required source role; requested/applied publication interval; item publication and observation time; requested/final locator; content kind; bounded content and native metadata; warnings; `ok|empty|partial|failed|refused`; bounded native reason; explicit loss; route eliminations/refusals; and optional opaque provider usage. Missing identity, secret/session/private data, public counters, normalized retryability, cache/async/enrichment/cluster fields, `LaneFinding`, confidence, verdict, accepted claim, or synthesis fails validation. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_pipeline.py" -v`, with a deliberately wrong result for every retained or forbidden field family. `oracle_class`: `deterministic`.
  5. Normalization is deterministic and bounded. Discovery hits group only when normalized locator and canonical hit-payload hash are equal; fetched records group only when fragment-free normalized final URL, content kind, and exact content hash are all equal. Every member's provider/request/upstream/query/rank provenance survives; same URL with changed content or observation payload remains distinct; exact duplicates cannot displace unique evidence under the frozen output cap; every bounded group is emitted in stable slice/native order. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_pipeline.py" -v`, including false-merge, provenance-drop, duplicate-displacement, and unstable-order fixtures. `oracle_class`: `deterministic`.
  6. The runner executes slices sequentially and exactly once, preserves earlier successes when a later slice fails, and records `ok`, `empty`, `partial`, `failed`, or `refused` with the native bounded reason and exact loss. No retry, fallback, relaxation, identity switch, internal engine fan-out, probe, cache lookup/store, or call after a terminal hard bound appears in the fake call ledger. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_pipeline.py" -v`, including prior-success-plus-failed-slice and forbidden-extra-call seeds. `oracle_class`: `deterministic`.
  7. `expand_site` exists only when the caller declares S3 and is runner behavior, never a third adapter/provider operation. It uses a deterministic frontier and repeatedly invokes the same authorized `fetch`; preserves an outcome for every attempted URL; uses conservative visited identity; refuses redirect-final off-origin targets; survives mixed page failures; terminates independently on page, depth, byte, or fake-clock time bounds; records the exact terminal bound reason; and makes zero calls after termination. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_pipeline.py" -v`, including query-order alias cycles, redirect-final-origin denial, mixed page failures, seeded cap overrun, and independent page/depth/byte/time bound fixtures. `oracle_class`: `deterministic`.
  8. The CLI tracer executes both explicit fake adapters across discovery, ordinary-lane-selected fetch, one exact duplicate, S2 empty/degraded distinction, prior-success-plus-failed-slice partial, refusal/no-route, malformed input, and conditional S3 expansion; it emits byte-stable canonical JSON containing artifacts, outcomes, route eliminations/refusals, warnings, loss, and gaps only. Exit is `0` for valid completed/partial output, `1` for valid refused/no-route output, and `2` for invalid input/internal contract failure. Provider-generated prose remains a tagged acquired item and is never parsed as accepted evidence; any lane dispatch, accepted-confidence, or final-synthesis output fails. Oracle: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -p "test_cli.py" -v`, using canonical goldens with one wrong seed per output/ownership family. `oracle_class`: `deterministic`.
  9. The result passes all project-item checks and the repository baseline with the resolved Python 3.9+ interpreter: `python -m unittest discover -s .orchflows/skills/search-fusion/tests -v`, `python tools/validate.py`, `python -m unittest discover -s tests -v`, `python install.py --dry-run`, and `git diff --check`. Oracle: command exit status and failure identity compared with the recorded starting revision, never test count alone. `oracle_class`: `deterministic`.
  10. A fresh review of the fixed result finds no correctness, contract-fidelity, scope, or code-craft shape defect; every changed line belongs to the stated project surfaces, project custom-item admission uses the library lens rather than host skill-creator validation, and the result preserves the ordinary-research ownership boundary. Oracle: `orch-critique` with `packs/orch-code-pack/references/lens.md`, independently rerun through `orch-verify`. `oracle_class`: `judged`.

- `binding_constraints`:
  - Python 3.9+ standard library only; offline and credential-free; exactly two explicit fake adapters in this delivery.
  - External repositories are evidence only. Reproduce documented mechanisms behind this package's own names and contracts; copy no external artifact or dependency graph.
  - Static imports and hardcoded call sites only. No reflection, entry points, metaprogrammed registry, arbitrary module/command value, executable shell string, or implicit adapter discovery.
  - One manifest schema and one artifact schema own every retained field; `references/protocol.md` is their only prose owner.
  - Base authority constants are `public`, `read`, `public_data`, and `run_only`; authorization and capability/freshness checks precede every adapter call.
  - S2 source roles are the caller-frozen community/social/news roles required by the ordinary lane. A route unable to enforce the requested publication interval refuses; an item outside or missing that interval cannot become `ok` evidence.
  - The utility never selects discovery hits. The caller supplies ordered hit IDs and the matching prior discovery artifact for the fetch invocation.
  - Adapter operations are exactly `discover` and `fetch`. S3 `expand_site` is runner-owned fetch reuse with same-origin and independent page/depth/byte/time caps.
  - Identical inputs produce byte-identical authorization, route, normalization, grouping, artifact order, and JSON. Provider ranks remain namespaced native metadata and never become confidence.
  - Exact grouping emits every bounded group, retains every member's provenance, and never treats provider/engine count as upstream independence.
  - Every slice has one attempt. Native reason and explicit loss survive unchanged; no terminal/transient or retryability normalization is public.
  - Hard-cap counters and the fake call ledger stay internal/test-only. Provider usage, when present, is opaque and cannot authorize another call.
  - The CLI emits canonical JSON; the ordinary research ticket owns persistence under its current run. The utility owns no cross-run store, cache, watch, history, verdict, or synthesis.
  - Tests are offline and fail-capable. The first dependency ticket freezes the four test files, fixtures, goldens, wrong-result seeds, exact commands, and starting baseline before production implementation; later tickets cannot weaken those oracles.
  - A user-scope orchflows installation is required to resolve the project custom item's call edges. The Claude adapter and AGENTS routing line follow project-scope law.
  - Preserve user changes and canonical source outside the listed surfaces. No terminal assembly item; merged green revisions are the code deliverable.

- `seams`:

  | Seam | Require | Return | Never |
  | --- | --- | --- | --- |
  | Manifest/schema | One versioned discovery, fetch, or conditional S3 runner request plus an optional prior discovery artifact | Validated typed data or invalid-input failure | Plan research, select a hit, contain a secret/session, or predeclare deferred state |
  | Authorize/router | Frozen base authority and one ordered static adapter roster | First eligible explicit route, or refusal/no-route with all eliminations | Perform I/O, probe health, score quality, reserve cost, or choose a fallback |
  | Adapter | One authorized `discover` or `fetch` request | Bounded native record, typed native outcome, warnings, timing, and optional opaque usage | Traverse, retry, plan, synthesize, persist, load arbitrary code, or mutate state |
  | Runner | Valid manifest, route, fake clock, hard caps, and optional prior discovery artifact | Sequential attempts, conditional fetch frontier, terminal outcomes, and exact loss | Auto-select hits, fan out engines, retry, switch identity, or call after a bound |
  | Normalizer | Native record plus manifest/route/attempt identity | Valid normalized items and conservative exact groups | Invent claims, erase warnings/loss, calibrate scores, or fuzzy-merge evidence |
  | CLI/export | Manifest plus admitted fixture inputs | Canonical JSON and frozen exit status | Emit research findings/confidence/synthesis or own cross-run persistence |
  | Skill boundary | Ordinary research acquisition ticket and bounded inputs | Acquisition artifact for lane-owned judgment | Cut lanes, accept claims, judge independence, or become a workflow owner |

- `affected_surfaces`:
  - `.orchflows/skills/search-fusion/SKILL.md`
  - `.orchflows/skills/search-fusion/references/protocol.md`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/__init__.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/schema.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/router.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/runner.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/normalize.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/cli.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/adapters/__init__.py`
  - `.orchflows/skills/search-fusion/scripts/search_fusion/adapters/fake.py`
  - `.orchflows/skills/search-fusion/tests/test_dependency_boundary.py`
  - `.orchflows/skills/search-fusion/tests/test_router.py`
  - `.orchflows/skills/search-fusion/tests/test_pipeline.py`
  - `.orchflows/skills/search-fusion/tests/test_cli.py`
  - `.orchflows/skills/search-fusion/tests/fixtures/**`
  - `.claude/skills/search-fusion/SKILL.md`, containing only host-legal frontmatter and an absolute `@`-include of the project item.
  - `AGENTS.md`, only one project-scope routing line outside managed blocks.
  - Runtime artifacts under `.orch/runs/<run>/` remain outputs, never implementation or instruction sources.
  - Explicit non-targets: `contracts/**`, `packs/**`, `skills/kernel/**`, `compositions/**`, top-level `scripts/**`, `install.py`, and managed instruction blocks.

- `required_absence`:
  - Do not create predecessor-proposed `references/schemas.md` or `references/policy.md`; `protocol.md` owns both concerns.
  - Do not create `catalog.py`, `preflight.py`, `planner.py`, `fusion.py`, `enrichment.py`, `lifecycle.py`, `degradation.py`, or `cache.py`; their retained behavior is merged into `router.py`, `runner.py`, or `normalize.py`, and all other behavior is absent.
  - Do not create `test_catalog_preflight.py`, `test_plan_router.py`, `test_schema_normalize.py`, `test_fusion.py`, `test_enrichment_lifecycle.py`, `test_degradation.py`, `test_cache_security.py`, or `test_tracer.py`; retained checks belong to the four named test families.
  - No live adapter file, provider SDK, generic HTTP/CLI adapter, credential reference, browser attachment, or external-skill artifact enters this delivery.

- `exemplars`:
  - `scripts/trace.py` at commit `7f01ba20adf51a3332adf5ac9d318eca8d333fa9`: imitate stdlib-only cross-platform code, explicit CLI seams, canonical JSON, bounded diagnostic records, and no traceback past the CLI; do not imitate its exit policy.
  - `tests/test_trace.py` at the same commit: imitate fixture-driven library/subprocess coverage, malformed inputs, exact output assertions, and helper-local temporary state.
  - `scripts/tickets.py` and `tests/test_tickets.py` at the same commit: imitate explicit parsing, stable machine output, adversarial wrong-result fixtures, and filesystem-boundary tests; do not copy ticket semantics.
  - `skills/utilities/orch-visualize/SKILL.md` at the same commit: imitate thin utility anatomy, explicit Require/Verify/Never/Return, and package-local ownership only; do not copy behavior, routed name, or canonical status.

- `routing`:
  - `pack`: `orch-code-pack`
  - `admission_owner`: `orch-build` at project scope; `search-fusion` is a custom acquisition utility and does not use the reserved `orch-` prefix.

- `bound`:
  - At most eight tracer-bullet tickets. The first dependency ticket freezes all tests, fixtures, goldens, forbidden seeds, exact commands, and baseline before production code; the first implementation ticket crosses manifest → authorize/route → both fake adapters → runner → normalize/group → export and proves S2 refusal plus one S3 terminal bound.
  - Production modules remain flat and approximately one-read size. Shared behavior moves only behind the seven named seams.
  - No live network call, login, credential value, authenticated browser, external installation, provider SDK, or external mutation during delivery or verification.
  - One code-lens gate, at most one combined correction pass, and one final `orch-verify` at the fixed result revision.
  - `plan_gate`: true; delivery stops after decomposition for user approval before any implementation ticket executes.

- `evidence`:
  - User request dated 2026-08-09: choose the simplest, most effective mechanisms from Agent Reach, Last30Days, and similar research tools; implement the winners as original hardcoded scripts under orchflows rather than importing whole skills.
  - Accepted adversarial synthesis `.orch/runs/20260809T132140Z-search-pareto/synthesis.md`, SHA-256 `BA71FD755898546FC1027BC07C5A9B8264517263721AF37F3819F4CE32A65EC2`; frozen acceptance 1–9 passed independent terminal verification.
  - Frozen predecessor native spec `.orch/runs/20260809T103759Z-native-search-fusion/spec.md`, SHA-256 `A1178C700B9CAE3A8390935ADF66C6DB9737AA9F949F7B87CB1C2F2675E22FD3`, used only as the complete keep/merge/defer/delete baseline.
  - Runtime composition `.orch/runs/20260809T132140Z-search-pareto/composition.md`, SHA-256 `EA337561E7F9523DDA6F8BD71B1C7EFF0612B437F3135F0E4EE84E28FC0C905C`, whose sequential edge admits this spec only after the synthesis identity exists.
  - Repository commit `7f01ba20adf51a3332adf5ac9d318eca8d333fa9` and the named standards owners/exemplars.

- `risks`:
  - Fake-only proof establishes the portable core contract, not live-provider quality, custody, schema stability, or deployment fitness. Each real adapter requires a separately accepted pinned protocol/deployment addition.
  - Fail-closed S2 capability checks can reduce coverage when an adapter cannot prove source-role or publication-interval enforcement; silent stale/unknown evidence is the rejected alternative.
  - Conservative exact grouping can under-group aliases; broader equivalence risks provenance-destroying false merges and remains benchmark-gated.
  - Deterministic bounded normalization is not yet proven on dynamic HTML, PDFs, or unsupported media; those inputs must expose typed loss rather than silently degrade.
  - Project scope is custom, not canonical law, and depends on the user-scope resolver documented by `orch-build`.

- `assumptions`:
  - The ordinary research lane can persist a discovery artifact and supply its identity plus ordered hit IDs to a later fetch invocation.
  - Two offline fake adapters are sufficient to prove the core seams; selecting and admitting a live adapter is a later owner decision, not an implicit implementation step.
  - A user-scope orchflows installation exists when the project item is invoked.
  - “Best features” means the accepted provider-neutral mechanisms and observable invariants, not every connector, UI, provider mode, or advertised optimization.

## Kind-count decision

One deliverable kind: `code`. The thin project utility contract, Python scripts, fake adapters, tests, fixtures, host adapter, and routing line form one executable result under `orch-code-pack`; research is frozen evidence, not a second deliverable in this successor run.
