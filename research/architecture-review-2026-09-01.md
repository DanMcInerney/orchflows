# orchflows architecture review — pass-2 synthesis

Run `20260901T155911Z`, ticket B1.6, synthesizing five pass-1 enumeration
lanes (B1.1 rules/docs/root, B1.2 scripts/, B1.3 tools/installer/reader/CI,
B1.4 packs/contracts/kernel/example-workflows/ring, B1.5 tests/) against
the tree at commit `58605b0f`. The five lanes returned roughly 1,700
findings total (B1.1 ~30, B1.2 ~1,170, B1.3 ~277 across six records, B1.4
~200, B1.5 ~45). This document does not re-list all of them — it
deduplicates by pattern, cites representative file:line evidence for each
pattern, and independently re-verified the highest-weight claims directly
against the tree (marked **[verified]** below) rather than taking any
lane's word for its sharpest findings. Review only, per Goal: no code in
this tree changed as part of producing it.

## Q1 — one-ownership findings, deduplicated by pattern

**P1. A live kernel skill instructs a mechanism the contracts it cites say is retired. [verified]**
`skills/kernel/orch-judge/SKILL.md:15-17` tells every judge dispatch to
"Write the complete seven-field findings array to one JSON file... the
join reads that file and binds it in the ledger." Two things are wrong
with this sentence, both confirmed directly: `contracts/shapes.json:179-186`
declares `verdict_criterion` with exactly five fields
(`verdict, oracle, oracle_class, evidence, covers`), not seven, and
`contracts/dispatch.md`'s own supersession log states plainly that
`dispatch-join` "adjudicates nothing and binds no findings... the
mechanical checker/repair selector that used to do that on
`--findings-file`/`--accepted-file`/`--artifact` retired with the
gate-stage ids." `contracts/result.md:42-51` says the same thing a third
way. This is not a docs-vs-docs mismatch — it is the actual instruction
every orch-judge dispatch reads, every run, contradicting the T0 contracts
it is bound by (B1.4 findings, corroborated independently in B1.4's
supplement by a second reading; both converge on this as the sharpest Q1
finding in their surface).

**P2. A verification-scope clause is restated verbatim in five files — not orphaned, since two mechanical readers consume it at dispatch time, but its law is still unstated in prose anywhere.**
"the full suite is the gate's row, never a unit's" (or a one-word variant)
appears in all five pack `craft.md` files —
`packs/orch-code-pack/references/craft.md:115`,
`packs/orch-content-pack/references/craft.md:108`,
`packs/orch-data-pack/references/craft.md:114`,
`packs/orch-design-pack/references/craft.md:121`,
`packs/orch-research-pack/references/craft.md:104` — **[verified]**
directly: `rules/verification.md`, the file `docs/vocabulary.md`'s
"unit" entry names as owning unit scope, contains the phrase nowhere.
**[corrected]** An earlier draft of this pattern called the five copies
"genuinely orphaned, not just duplicated." They are not — two mechanical
owners consume this exact clause, both missed on that pass.
`tools/validate_support/duplication.py:44-66` registers a declared
duplication family, `"verification-scope anchor"`, whose `reason` field
states the case verbatim: "Every pack carries this sentence by that
mandate, not by drift... the closing clause states the shared law
itself, which has exactly one wording," with the canonical clause list
at `:58-65` ending in the exact string at `:64`. And `scripts/
tickets_assignment.py:50-54` declares `CRAFT_SCOPE_ANCHOR = "gate's
row"`; `_craft_scope()` (`:140-165`) scans each craft's `## Stages`/
`## Lens` bullets for that literal anchor and quotes the matching
sentence into every dispatch's launch prompt — live machinery, not idle
prose (this document's own drafting ticket carried exactly that quoted
sentence, verbatim, on its own launch). The five restatements are a
reasoned, registered exemption from single ownership, not neglect. What
is genuinely missing is narrower than "orphaned": `rules/verification.md`
states the law nowhere in prose, so a reader following
`docs/vocabulary.md` to the file it names as owning unit scope finds
nothing there.

**P3. `ORCHFLOWS_STATE_HOME` is redeclared as a named constant at least twelve times, only one of which is the owner — "nine" undercounts.**
`scripts/state_root.py:38` owns `ENV_VAR = "ORCHFLOWS_STATE_HOME"`. Eight
independent module-level redeclarations of the identical string exist:
`tests/__init__.py:36`, `tests/test_harvest.py:41`,
`tests/test_friction_cases/common.py:42`, `tests/test_project_binding.py:40`,
`tests/test_migrate_state_cases/common.py:29`,
`tests/test_workspace_cases/common.py:32`,
`tests/test_tickets_cases/common.py:56`,
`tests/test_installer_cases/support.py:215`, plus a ninth in production
code: `tools/suite_check.py:206-207` (whose own comment admits it cannot
import `state_root.py` "for bootstrap-ordering reasons"). One file,
`tests/test_state_root_cases/support.py:22`, does it correctly
(`ENV_VAR = state_root.ENV_VAR`), proving the pattern is avoidable, not
forced (B1.5 addendum-2's exact count; corroborated by B1.1, B1.2, B1.3
independently hitting the same fact from three different surfaces). **The
count still undercounts.** At least three more independent module-level
redeclarations exist beyond the nine above — **[verified]** directly:
`installer/foundation.py:151` (`STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"`),
`reader/tests/test_ui_cases/root_resolution.py:16`, and
`reader/tests/test_ui_cases/_base.py:38` (both
`SINK_ENV_VAR = "ORCHFLOWS_STATE_HOME"`) — putting the real total at
twelve-plus, not nine, and correspondingly raising T3's "9 + 20+ = 29
duplicate sites" fan-out claim by the same three.

**P4. No tree-root or state-root resolver is actually shared — ~20+ files each re-derive `__file__`-relative paths independently.**
`tools/affected_tests.py:50`, `tools/check_source_sizes.py:21`,
`tools/live_claude_profiles.py:24`, `tools/live_codex_profiles.py:20`,
`tools/live_routing_bench.py:29`, `tools/live_sweep_e2e.py:38`,
`tools/preflight.py:33`, `tools/regen.py:45`, `tools/render_hosts.py:12`,
`tools/render_lifecycle.py:12`, `tools/render_shapes.py:12`,
`tools/run_report.py:40`, `tools/run_required.py:26`,
`tools/run_serial_compat.py:25`, `tools/run_super_research_tests.py:12`,
`tools/run_tests.py:33`, `tools/validate.py:28`,
`tools/validate_measures_support/common.py:10`, `tools/verify_at.py:54`
each independently compute `Path(__file__).resolve().parent...` with
inconsistent spellings (`.parent.parent` vs `.parents[1]`) for the same
"repository root" fact; none imports a shared resolver (B1.3 tools/
findings). This sits beside, but is distinct from, P3's env-var
duplication — one is "what env var names the sink," the other is "where
is the repo root" — and both stem from the same cause: `tools/` cannot
import `scripts/state_root.py` without creating an import-order problem,
so every file re-solves the bootstrap independently rather than one file
solving it once.

**P5. Cross-reference citations name the wrong section — invisible to the link checker because the target exists.**
`README.md:91` cites `rules/topology.md` §2 as the routing table's owner;
topology.md §2 is actually about ticket/cut shape-sizing at intake and
never mentions the routing table (owned by the host block, per
`docs/vocabulary.md:169-170`). `docs/custom-workflow-authoring.md:230`
cites "documentation laws 5–6" for "implemented enforcement and
non-normative illustrations"; law 5 is about name resolution, law 9 is
the actual match for "non-normative illustrations" (B1.1). Separately,
`templates/host-block.md` cites `rules/visibility.md` §6 for the
state-root law at line 35 and §3 for the same law at line 54 — two
different section numbers for one fact inside one file (B1.4). All three
are undetectable by `tools/validate.py`'s doclint, which resolves that a
cited file and anchor exist but never checks that the cited clause says
what the citing prose claims it says.

**P6. Status/role/host rosters are hand-restated as literals in three-plus independent files each.**
The two-entry role map (`orch-do`→worker, `orch-judge`→planner) is stated
correctly once at `scripts/tickets_registry.py:34-36`
(`EXECUTOR_REGISTRY`) and then independently retyped at
`tests/test_static_tree_invariants_cases/skill_packages.py:10-13`
(`ROLE_TABLE`) and `tests/test_thin_orchestrator.py:44-47`
(`WORKFLOW_ROLES`) — three files, one fact, zero of the two copies
importing the owner (B1.5). The host roster `("claude","codex","grok")`
is independently declared at `installer/hosts.py:13`,
`scripts/orchflows_adapters.py:43`, and
`tests/test_catalog_completeness.py:37`, under three different variable
names (B1.5). Retired-executor rosters diverge further: `scripts/
tickets_registry.py:55-73`'s `SUPERSEDED_EXECUTORS` names nine retired
verbs; `tests/test_static_tree_invariants_cases/compositions.py:80-84`
checks only four of them absent; `tests/test_static_tree_invariants_cases/
benchmark_architecture.py:43-46` checks a fifth, wholly disjoint roster
of five more dead names never in the registry at all; `tests/
test_command_surface.py:59-63` and `tests/_retired_doors.py:26-31` name
two more non-identical "retired subcommand" rosters (B1.5). Five
independent, partially-overlapping "what used to exist" lists, no index
tying them together.

**P7. Ticket lifecycle-state literals bypass their own owner.**
`scripts/tickets_transitions.py:18` owns
`PENDING, READY, CLAIMED, SUSPENDED = "pending", "ready", "claimed",
"suspended"`. `scripts/tickets_seal.py` correctly imports `CLAIMED` from
it. At least eight other call sites re-derive the same literals as bare
strings instead: `scripts/tickets_attempts.py:124,174,190,253,498`,
`scripts/tickets_dispatch_facade.py:258`, `scripts/tickets_outcome.py:75`,
`scripts/workspace_git.py:511`, plus `"pending"` independently hardcoded a
further five times across `scripts/tickets_brick.py:228`, `scripts/
tickets_frame.py:105`, `scripts/tickets_issue.py:123,173`, and `scripts/
tickets_lint.py:37` (B1.2 cross-group finding + Group C). One correctly-
demonstrated pattern (`tickets_seal.py`), thirteen-plus bypasses.

**P8. A path/key constant owned by one module is hardcoded as a bare literal by its own siblings.**
`scripts/workspace_git.py:44-45` owns `BRANCH_KEY`/`BASELINE_KEY`
("workspace_branch"/"workspace_baseline"); `scripts/tickets_dispatch_
facade.py:117,212-213`, `scripts/tickets_land.py:212-213`, and `scripts/
tickets_assignment.py:100` each hardcode the same two strings instead of
importing them (B1.2 Group E1). `scripts/workspace_record.py:16` owns
`PATH_KEY` ("workspace_path"); `scripts/tickets_dispatch_facade.py:123,221`
and `scripts/tickets_dispatch_validate.py:72` each hardcode it
independently. The pattern recurs for `join:`/`lifecycle:` record
prefixes (owned by `scripts/tickets_dispatch_identity.py:32`, bypassed at
`scripts/tickets_land.py:75`, `scripts/tickets_join.py:115`, `scripts/
tickets_dispatch_facade.py:236`) and for `"receipt.json"`, hardcoded four
times (`scripts/tickets_store.py:256`, `installer/doctor.py:397`,
`installer/planning.py:136,448`, `installer/uninstall.py:181`) with no
resolver owning the name (B1.2 Group A/B).

**P9. A phrase-anchor test-pinning pattern makes the test suite a second, undeclared owner of dozens of prose facts.**
`tests/test_constitution.py:40-58`, `tests/test_architecture_owners.py:
37-42`, `tests/test_registry_census.py:228-260`, `tests/test_serial_
compat.py:349-360`, and — most extensively —
`tests/test_installer_cases/managed_text/host_block.py:118-213` (whose own
header comment calls the pattern "nine gutted copies, nine silent") each
assert that an exact phrase from a specific prose file is present verbatim,
rather than parsing the file and checking structure. This is not always
wrong (`tests/test_architecture_owners.py:27-29`'s `CEILING_RE` reads
ARCHITECTURE.md's word ceiling at test time instead of hardcoding it — the
right pattern, present in the same surface as its own contrast case) but
it means dozens of prose sentences across `docs/library-review.md`,
`ARCHITECTURE.md`, `templates/host-block.md`, and `tools/serial-compat-
policy.md` are now load-bearing test fixtures: editing the prose without
also editing the test breaks CI, and the test suite itself becomes a
second normative "owner" of wording rules/visibility.md §3 says should
live in exactly one file (B1.5).

**P10. CI topology is stated three ways, and the most-quoted one is wrong. [verified]**
`tools/preflight.py:4`'s docstring, pinned unchangeable by `tests/
test_preflight.py:9-12`, states the matrix as "three Ubuntu, one macOS,
and one Windows." I simulated `.github/workflows/checks.yml:88-112`'s
`os`/`python-version`/`shard` axes against its seven `exclude` entries
directly: the five surviving legs are two Ubuntu (3.9/1-of-1,
3.13/1-of-1), one macOS (3.13/1-of-1), and two Windows (3.13/1-of-2,
3.13/2-of-2) — **two Ubuntu, one macOS, two Windows**, matching
checks.yml's own inline comment ("Windows alone is split, and only in
two"). `tests/tree_removal.py:15-18` states a third, also-wrong breakdown
("three Windows legs... on none of the other six" — the actual non-Windows
count across both workflow files is five, not six). Total leg count (5)
is right everywhere; every stated per-OS breakdown is wrong, and the two
wrong breakdowns disagree with each other as well as with the truth.

**P11. Reader duplicates trunk knowledge across the process boundary, and duplicates within itself besides.**
`reader/scripts/ui_model.py:18` and `reader/scripts/ui_discovery.py:47`
both self-document as "the reader's copy" of the sink layout `scripts/
state_root.py`/`scripts/tickets.py` own — a deliberate, acknowledged
duplication (reader is a separate deployable, plausibly cannot import
`scripts/` directly). Less defensible: `reader/scripts/ui_artifacts_
projection.py:28`'s `NAME_RE` is byte-identical to `reader/scripts/
ui_workflows_identity.py:18`'s, in a file that already imports that
module; `REDACTED_HOST_PATH` is independently redefined three times
inside reader/scripts alone (`ui_experience.py:52`, `ui_artifacts_
projection.py:37`, `ui_workflows_sources.py:24`) with a fourth, differently-
worded copy on the TypeScript side (`reader/web/src/features/friction/
model.ts:17`); and `reader/scripts/ui_layout.py:11`'s server-side layout
constants compute node positions the browser discards and recomputes with
independent constants (`RunMapView.tsx:140`, `elk.worker.ts:40`,
`layout.worker.ts:12`) — dead server-side work maintaining a duplicate
that is never used (B1.3 note-02).

**P12. Documentation states facts about the current tree that are simply false.**
`reader/docs/platform.md:78-89`'s routes table omits four live routes
(`/api/v1/views/{view}` and three `/api/v1/workflows...` routes, all
declared in `reader/scripts/ui_workflows_projection.py:20-27` and
`ui_api.py:302`), and separately, at `:138`, states "62 deterministic
identities" against an actual, enforced 64 (`reader/tools/
ui_frontend.py:347`). `reader/docs/modularization.md:7` describes a
"baseline" of files (`app/registry.ts`, `state/location.ts`, etc.) that
do not exist anywhere in the current `reader/web/src` tree — the
migration it frames as pending is already done. `DESIGN.md:190` states
the pack-craft validator enforces "a 60-non-empty-line budget";
**[verified]** directly, `tools/validate_support/common.py:61` enforces
`CRAFT_BUDGET = 130`, and every live craft.md file (81–100 non-empty
lines) sits under 130 but would violate 60 if that number were real.
`.orchflows/skills/super-research/scripts/super_research/cli.py:13` states
"the thirteen probe declarations"; **[verified]** directly,
`probes.py`'s own `SMOKE_PROBES` tuple and its header comment ("Twenty-
five probes, one per live adapter") declare 25, one per distinct
`adapter_id` — the module grew and the docstring that describes its own
sibling did not. These are not migration-debt or metaphor issues — they
are stale factual claims a reader would act on.

Separately, and not a false-fact but a naming collision: `example-
workflows/super-research/SKILL.md:2` and the ring's
`.orchflows/skills/super-research/SKILL.md:2` both declare `name:
super-research` — one pre-migration example-workflow and one live
project-ring item sharing an identical frontmatter name. No collision in
a live registry was found on inspection, so this is filed as a naming
hazard, not a confirmed breakage.

**P13. A green test can pass for the wrong reason — the review had no
finding class for this, and it should have.** `tests/test_tickets_cases/
identity_terminal.py:310`'s
`test_every_ticket_writing_subcommand_reports_and_lands_nowhere` exercises
a `check` subcommand that no longer exists in `scripts/tickets.py`'s CLI
surface; the assertion (`returncode == 1` and `"error"` in the JSON
payload) is satisfied by an "unknown subcommand" refusal, not by the
sink-unwritable law the test's name and docstring claim to exercise. The
test is green and proves nothing. The same lane's Report names sibling
dead weight in the same file family: unused test helpers `SequencedPath`,
`refusing_to_read`, `refusing_to_write` in
`tests/test_tickets_cases/common.py:248,288,328`, and a duplicated
`import` of `tickets_dispatch_facade` at `tests/test_lock_discipline.py`
(two identical `from scripts import tickets_dispatch_facade` lines,
confirmed adjacent in the file's import block) — **[verified]** directly
for all four. `MANIFEST_BUDGET` (Q2 table below, `common.py:32`) is the
same failure mode one layer up: a declared constant with zero consumers.
None of P1–P12 above is shaped to catch "the check exists and is green"
as distinct from "the check is correct" — this pattern needs its own
name because a reader trusting suite-green as proof of the sink-unwritable
law is exactly the reader this report exists to protect.

## Q2 — limits enumeration, deduplicated by pattern

The five lanes together enumerated roughly 300 distinct numeric limits.
They fall into five kinds, and the kind determines the verdict:
(a) terseness budgets (word/line/character ceilings on prose surfaces —
these are the ones the Goal asks to consolidate); (b) protocol/data-shape
bounds (byte/char caps on a closed wire format, e.g. `scripts/
search_plan_protocol.py:9-11`'s `MAX_INPUT_BYTES=1_000_000`); (c) operational
timeouts and retry budgets (one per resource — `installer/runtime.py:127`'s
10s health-probe timeout, `scripts/friction.py:66`'s 2s git-rev timeout,
`scripts/tickets_store_writes.py:35-36`'s 2.0s/0.005s replace-retry
budget); (d) rate-limit/pacing constants (one per external origin,
empirically measured — `.orchflows/skills/super-research/scripts/
super_research/adapters/github_rest.py:73-75`'s `min_interval_ms=60000` matching
GitHub's documented 60/hr ceiling); (e) CI/toolchain pins (Python 3.9/
3.13, Node `'24'` vs `reader/package.json:7`'s `>=20.19.0`, pnpm
`10.32.1` pinned independently in two files). Only (a) answers to "fewer
limits, keep only those enforcing terseness" — the per-limit verdict
table below treats (b)–(e) as a different question with its own,
narrower single-owner fixes, stated per item.

## Q3 — cohesion and vocabulary findings, deduplicated by pattern

Ticket Details rules "brick" out of the vocabulary already; every other
load-bearing term found is scored here against the same test — simple,
self-explanatory, mechanism stated in plain words, no metaphor unless it
is already standard computing usage (kernel, cache, shard, sentinel), and
metaphor confined to human-facing docs.

| Term | Sense count found | Verdict | Evidence |
|---|---|---|---|
| **brick** | 1 (consistent) | **Fails — rename.** Already ruled. | ~45 rules/docs/root sites (B1.1), full `scripts/tickets_brick.py` + admission/frame/registry family (B1.2 Group B/C), `contracts/work-item.md` ×10 + `self-improve/SKILL.md` ×3 (B1.4), 100+ `tests/` sites across 11 files (B1.5), installer-generated adapter text (B1.3 note-04). Zero occurrences in the ring (super-research) or the kernel SKILL.md bodies themselves — the rename's blast radius is entirely in scripts/, contracts/, tests/, docs/, not in the two files that define the callables. |
| **frame** | 1 (consistent) | **Fails — rename together with brick.** | Same family; `scripts/tickets_frame.py` (~90 sites), `contracts/work-item.md`, `docs/vocabulary.md`. |
| **seal / sealed** | 1 (consistent) | **Fails — rename together with brick.** | `scripts/tickets_seal.py`, `tickets_admission.py` (~110+ sites, B1.2 Group B addendum), `assignment_seal` field name everywhere in shapes.json-generated code. Highest per-file density of any term reviewed. |
| **gate** | **5 distinct, unconnected senses** | **Fails hardest — disambiguate before renaming.** | (1) `"independence": "gate"` ticket field; (2) the retired composite-gate/`GatePlan` topology, explicitly dead; (3) informal "dogfooded gate"/gate-stage review checkpoint; (4) prompt-text reuse of the retired composite-gate naming; (5) generic CI/validation-gate sense in `tests/test_regen.py`. Plus P2's pack-craft clause "the gate's row" is a sixth, cross-cutting usage. `docs/vocabulary.md` gives "gate" no bolded entry of its own anywhere (B1.5). Worst term in the review by sense-count. |
| **door** | 1, but never formally defined | **Fails — either define once or fold into brick/frame's rename.** | Load-bearing inside the brick/launch entries (`docs/vocabulary.md:29-32`) but has no bolded entry of its own, unlike brick/frame/waist; occurs standalone, undefined, at five more test sites (B1.5). |
| **lane** | **4-5 distinct senses** | **Fails — rename the non-canonical senses.** | Canonical: "isolated parallel candidate" (`vocabulary.md:328`). Also used for: a workspace-establishment strategy branch (`workspace_candidate.py:11`), a benchmark/probe category (`live_sweep_e2e.py:2`), a test-execution mode (`run_serial_compat.py:3`), a CI parallel job/leg (`validate_measures.py:12,126`), and a "checker lane" (`tickets_brick.py:78`). Six senses, one vocabulary entry. |
| **trunk** | 1, informal only | **Passes conditionally — already confined to non-normative rationale (`DESIGN.md:348,511`); leave as informal prose.** This review's own trunk/leaf section below uses the word the same way, deliberately. | 2 sites, not in `docs/vocabulary.md`. |
| **waist / narrow waist** | 1 (consistent) | **Passes — standard systems-architecture term (hourglass model), formally defined once, small footprint.** | `vocabulary.md:19-20`, 4 sites total. |
| **kernel** | 1 (consistent) | **Passes — standard CS usage (minimal core), formally defined, used correctly everywhere checked.** | Widely and consistently used per `vocabulary.md`'s own definition. |
| **ring / bundle / trust ledger / shadow notice / surface / pin** | Each 1 sense, but **zero of them has a `docs/vocabulary.md` entry** | **Fails on documentation, not on metaphor.** "Ring" is domain-standard-adjacent (plugin/extension "rings") but is the central noun of five files (158 occurrences) and entirely undocumented (B1.2 Group E2). | Add entries; not rename candidates — candidates for finally being written down. |
| **ladder / rung** | **3 conflicting senses**: dispatch-escalation vehicle (canonical, `vocabulary.md`), benchmark measurement tier (`tools/validate_measures_support/`, ~50 sites), workflow measurement-pass tier (`example-workflows/references/benchmaker-protocol.md:101,105,111`) | **Fails — the two non-canonical senses need their own words.** | Benchmark "rung" and canonical "rung" never collide in the same file, but collide in any full-tree search — rename the benchmark sense to "tier" and separately disambiguate `orchflows_home.py:15`'s informal "npm's global tier" from the formal T0–T3 "tier" while at it. |
| **seam / sentinel / shard / protocol / checkpoint / disposition** | Each pervasive (seam: 70 files; shard: 21; sentinel: 4) but **undefined** | **Not metaphors — standard testing/CI/protocol vocabulary. Fails only on documentation.** | Same fix as ring: add entries, do not rename. `disposition` alone carries three unrelated closed sets (dispatch outcome, browser-game checkpoint choice, installer role); flag for disambiguation even though it stays undefined-by-design elsewhere. |
| **judge (noun)** | Collides with the `orch-judge` callable | **Fails — the noun predates the callable and both are now live; disambiguate.** | `docs/vocabulary.md:235-239` already self-acknowledges this as open "naming debt," and the friction-log entry that raised it (2026-08-31) is still unresolved at the current commit — the one collision the codebase already knows about and has not fixed. |
| **Legos / stud / snap** | README-only, undefined | **Passes — human-surface metaphor, correctly exempt** per `docs/documentation.md:6`. | 3 sites, all `README.md`. |

**Assembled brick rename map** (the mechanism for landing this is T9,
below): every file family carrying "brick"/"bricks" — `docs/
vocabulary.md`, `rules/verification.md`, `rules/topology.md`, `rules/
delegation.md`, `ARCHITECTURE.md`, `DESIGN.md`, `README.md`, `TICKETS.md`,
`docs/library-review.md`, `docs/custom-workflow-authoring.md` (B1.1); the
whole `scripts/tickets_brick.py` module plus every importer (`tickets_
dispatch.py`, `tickets_frame.py`, `tickets_commands.py`, `tickets_
format.py`) and every `BRICK_*`-prefixed constant (B1.2 Group B/C);
`contracts/work-item.md` (×10), `contracts/dispatch.md` (×2), `contracts/
result.md` (×2), `example-workflows/self-improve/SKILL.md` (×3) — and
explicitly **not** `skills/kernel/orch-do/SKILL.md` or `skills/kernel/
orch-judge/SKILL.md` themselves, which use the word zero times (B1.4);
`installer/packages.py` (×3, rendered into shipped adapter text, so the
rename must also re-render every installed surface); the ring
(`.orchflows/skills/super-research/`, zero occurrences — nothing to touch
there); and
`tests/test_ticket_bricks.py` plus 10 sibling test files (~100+
occurrences, B1.5).

**Other Q3 cohesion findings** (misplaced module boundaries, not
vocabulary): `scripts/browser_game_validate.py` and 310-line `tools/
validate_support/browser_game.py` are both entirely specific to one named
example-workflow's domain, living in generic trunk territory rather than
under `example-workflows/browser-game/` (B1.2 Q3; see Trunk/leaf map
below). `installer/managed_text.py:38-41`'s Grok limit-block renderer
sits away from its three sibling `GROK_MAX_*` constants in `installer/
foundation.py` "only because foundation.py is outside this ticket's
write scope" — the file's own comment names a stale ticket-authoring
boundary, not a domain reason (B1.3 note-04). `scripts/tickets.py:280-325`'s
`_sync_seams()` reaches into and rewrites roughly a dozen sibling
modules' globals — wiring work well beyond ARCHITECTURE.md's description
of an unprefixed family module as "the public command and import facade"
(B1.2 Group B).

## Thread synthesis — one architectural change per thread

Each thread below names the *one* change that dissolves every finding in
its pattern class. None of these are per-finding patches; per-finding
patches are what produced the ~300 duplicate-literal findings in the
first place.

**T1 — Rewrite `orch-judge/SKILL.md`'s Return clause against the live contract, now.**
Dissolves P1. Delete "Write the complete seven-field findings array to
one JSON file... the join reads that file and binds it in the ledger."
Replace with what `contracts/dispatch.md` and `contracts/result.md`
already say: findings travel in the free-text `## Report` like any other
filing; the repair answering a critique is an ordinary `do` brick under
the same parent. This is the single highest-leverage fix in the whole
review — it is not a documentation nicety, it is the literal instruction
loaded on every judge dispatch, and it currently tells the model to build
a mechanism that does not exist.

**T2 — State the verification-scope law once in `rules/verification.md`, additively; leave every craft.md sentence untouched.**
Answers P2's real gap, not the one first stated. The naive fix — replace
each craft.md sentence with a link to `rules/verification.md`, per
`rules/token-economy.md` §6's "a link states at its call site when to
follow it" — would break live dispatch: `CRAFT_SCOPE_ANCHOR`
(`scripts/tickets_assignment.py:50-54`) matches the literal string
"gate's row" inside each craft's `## Stages`/`## Lens` bullets, and
`_craft_scope()`'s own docstring (`:144-145`) says "a craft that
declares no scope gets no quote, and the prompt's standing line answers
alone" — replace the sentence with a link and the anchor matches
nothing, silently degrading every dispatch across all five packs to the
generic standing line. The safe fix is additive only: state the law in
`rules/verification.md` for a reader browsing `rules/`, keep every
craft.md sentence exactly as written, and treat any future edit to those
five sentences as bound to keep `CRAFT_SCOPE_ANCHOR` matching.

**T3 — One bootstrap-safe root/env resolver, importable before `scripts/` proper.**
Dissolves P3 and P4 together, because they are the same root cause: no
file below `scripts/state_root.py` in the import order can reach it
without a circular or bootstrap-ordering problem, so 20+ files each
re-solve "where is the repo root" and 12+ files each re-solve "what env
var names the sink" (P3's corrected count). The fix is not "import
state_root.py everywhere" (that is what caused the ordering problem
`tools/suite_check.py:202`'s own
comment names) — it is a new, deliberately tiny, zero-import leaf module
(e.g. `scripts/_bootstrap.py`, under 20 lines) holding exactly the env-var
name and the `__file__`-relative root-walk, that `state_root.py` itself
imports from and every currently-duplicating file switches to import
from instead of redefining. One new file, ~29 deletions.

**T4 — Generate cross-references from the same source the target renders from, instead of hand-typing section numbers.**
Dissolves P5. `tools/render_shapes.py`, `render_hosts.py`, and
`render_lifecycle.py` already prove this pattern works for generated
tables; extend it to cross-file citations by having `tools/validate.py`'s
doclint resolve a citation's *heading text*, not just its file+anchor —
a citation to "rules/topology.md §2" should fail if §2's actual heading
text does not match a declared expectation, the same way a broken link
already fails. This turns three (and future) wrong-section citations from
invisible to loudly caught, for the cost of one new check.

**T5 — One roster module for every closed "which names exist / are retired" fact, imported everywhere a roster is currently retyped.**
Dissolves P6. `scripts/tickets_registry.py` is already the closest thing
to this owner (`EXECUTOR_REGISTRY`, `SUPERSEDED_EXECUTORS`,
`CALLABLE_EXECUTORS`); the fix is not a new file, it is closing the
roster's coverage (folding in the five names `benchmark_architecture.py`
tracks that the registry does not, and the two CLI-subcommand rosters)
and then treating any test file that retypes a subset as a bug the same
way `tests/test_state_root_cases/support.py`'s correct-pattern contrast
case already proves is achievable for env vars.

**T6 — One status/lifecycle-literal law: a lint rule refuses a bare `"pending"`/`"claimed"`/`"complete"`/`"suspended"` string literal outside `tickets_transitions.py` itself.**
Dissolves P7 and (for `workspace_branch`/`workspace_baseline`/
`workspace_path`/`join:`/`lifecycle:`) P8. `tools/validate_support/
duplication.py` already runs a near-duplicate literal scan
(`CELL_SIMILARITY_THRESHOLD`); add a second, narrower AST-level check for
the closed set of lifecycle/record-prefix strings specifically, since
those are not prose near-duplicates but exact string literals with one
declared canonical source each.

**T7 — Fold the phrase-anchor test-pinning pattern into the same duplication check T6 extends, scoped to test files against prose sources.**
Dissolves P9. The right pattern already exists twice in this exact
surface (`test_architecture_owners.py`'s `CEILING_RE`, `test_state_root_
cases/support.py`'s `ENV_VAR` alias) — this is not a new mechanism to
invent, it is enforcing the pattern the codebase already demonstrates
working, the same way T3 and T5 do for their own patterns. Where a test
must assert exact prose (regression-testing the prose itself, as
`test_windows_semantics.py` legitimately does), the fix is not to stop
pinning — it is one canonical location generating the pinned phrase, per
T4.

**T8 — Render the CI-topology sentence from the workflow YAML; delete every hand-typed count.**
Dissolves P10. This is the same fix as T4, applied to one especially
sharp instance: a `tools/render_ci_topology.py` (or an extension of the
existing render family) that reads `.github/workflows/checks.yml`'s
matrix/exclude rules and `serial-compat.yml`, computes the leg
breakdown the way this review's own verification did, and stamps it into
`tools/preflight.py`'s docstring and `tests/tree_removal.py`'s docstring
as a generated block. Zero future drift is possible once the sentence is
derived instead of authored.

**T9 — One rename pass for "brick," executed as one architectural change, not per-file edits.**
Dissolves the "brick" occurrence map (assembled above, Q3). The planned
rename is already ruled — this thread names the mechanism: a single
`tools/rename_term.py` (or a scripted `sed`-equivalent run once, reviewed
once) that touches every site in the map above in one commit, because a
term this pervasive (roughly 45 rules/docs/root-doc sites, several hundred
scripts/ sites, ~100+ tests/ sites, 3 example-workflow sites, several
installer-generated-text sites) cannot be safely edited piecemeal without
leaving the exact half-migrated-metaphor state the 2026-08-31 lego-
migration friction log already shows happened once before (five friction
entries naming a split rename across two branches as the direct cause of
stale constants).

**T10 — Apply the same self-explanatory test to every other metaphor term, in the same pass as T9, and land only the terms that fail it.**
See the metaphor audit table above. This thread's single change is: add
one sentence to `docs/vocabulary.md`'s own preamble — "a term names its
mechanism in plain words; a metaphor is permitted only where it is
already domain-standard computing usage (kernel, cache, shard, sentinel),
never invented for this library" — and then apply it once, in the T9
commit, to the terms that fail it (frame, seal, the non-canonical senses
of gate/door/lane/rung).

## Numeric limits — single-config-file evaluation and per-limit verdicts

**The single-config-file root fix is the correct shape for kind (a) —
terseness budgets — and wrong for kinds (b)–(e).** A config file's job is
holding editorial numbers a human tunes by review evidence, per `rules/
token-economy.md` §11's own closing paragraph ("A ceiling only falls, and
falls on evidence... never on taste"). Protocol bounds, timeouts, and
pacing constants are not editorial — they are correctness facts about a
wire format, a subprocess, or a third party's measured rate limit, and
moving them into one shared file would just create a second place they
can silently drift from the code path that actually enforces them. Kind
(a) earns the config file; kinds (b)–(e) each keep their existing
single-file owner, named explicitly below with the reason.

**What earns a place in the config file** (currently spread across
`rules/token-economy.md` prose, `rules/composition.md`, and `tools/
validate_support/common.py`'s Python dict, three places for numbers that
are logically one table):

| Limit | Value | Current owner(s) | Verdict |
|---|---|---|---|
| Host block body | 400 words | `rules/token-economy.md` §11 (prose) + `tools/validate_support/common.py:31` `SURFACE_BUDGET` (enforced) | **Move to config.** Prose states it a second time for no reason once the config file is the cited source. |
| Project routing block | 400 words | `rules/token-economy.md` §11 (prose only — **not enforced anywhere**, per B1.3's grep) | **Move to config, then enforce it.** Currently the one every-turn ceiling with no validator check at all. |
| `AGENTS.md` | 230 words | `token-economy.md` §11 + `common.py:31` | **Move to config.** |
| Role agent file | 80 words | `token-economy.md` §11 (prose only — not independently enforced under this name; `tests/test_installer_cases/managed_text/roles.py:52` enforces `BODY_CEILING=80` for the *rendered* Claude agent body, a related but distinct surface) | **Move to config**, and confirm at review time whether the un-rendered role-agent-file ceiling and the rendered-body ceiling are meant to be the same number or two numbers currently coinciding by accident. |
| Kernel skill body | 300 words | `token-economy.md` §11 + `common.py:24` | **Move to config.** |
| Pack `SKILL.md` body | 150 words | `token-economy.md` §11 + `common.py:26` | **Move to config.** |
| Workflow body | 450 words | `token-economy.md` §11 + `common.py:25` | **Move to config.** |
| Skill `description` | 140 chars | `rules/composition.md:19` + `common.py:33` `DESCRIPTION_BUDGET` (already the same number, two owners) | **Move to config; delete the composition.md restatement, link instead.** |
| Pack craft.md body | **60 lines stated, 130 enforced — a live contradiction [verified]** | `DESIGN.md:190` (stale, states 60) vs `tools/validate_support/common.py:61` `CRAFT_BUDGET=130` (actual, enforced) | **Change-with-proposed-value: fix DESIGN.md to say 130 (or lower the enforced value toward the real craft.md sizes, 81–100 lines, if 130 is judged too loose) — either way, move the number to config and delete the DESIGN.md hardcoded figure entirely.** This is the single most concrete Q2 defect: a stated budget nobody is actually held to. |
| `ARCHITECTURE.md`'s own ceiling | 925 words | `ARCHITECTURE.md:3` (stated) — **enforced [verified], by the same pattern P9 credits as "the right pattern":** `tests/test_architecture_owners.py:27-29`'s `CEILING_RE` reads the number out of the prose at test time (`stated_ceiling()`, `:64-68`), and `test_the_map_is_inside_the_ceiling_it_states` (`:87-88`) asserts the map's own word count against exactly that number. B1.3's "zero hits" grep was scoped to `tools/*.py` and missed `tests/`, where the enforcement actually lives. | **Keep the number in the prose; do not move it to config as originally written here.** Deleting `ARCHITECTURE.md:3`'s number, as a bare "move to config" would, leaves `CEILING_RE` matching nothing and silently removes the enforcement — the opposite of this row's own stated intent, and a contradiction of P9's verdict on the identical construct. If the twelve-row config file below lands, this row's number stays in `ARCHITECTURE.md:3` and the config carries a copy `CEILING_RE` is repointed at, not a replacement for it. |
| `docs/vocabulary-authoring.md` | 40 lines | Self-declared, own file only | **Move to config** — same class as the others, currently the odd one out stating its own number inline. |
| Manifest budget | 250 | `common.py:32` `MANIFEST_BUDGET` — **dead, consumed nowhere** | **Delete.** Not a candidate for the config file; it is unused. |

**What stays multi-owner, and why** (the ticket asks for a stated reason
per item; the load-bearing ones):

- **Search-plan protocol bounds** (`MAX_INPUT_BYTES=1_000_000`,
  `MAX_IDENTITY_CHARS=256`, `MAX_DECIMAL_CHARS=128`,
  `scripts/search_plan_protocol.py:9-11`) stay owned by
  `scripts/search_plan_protocol.py` alone, with
  `docs/search-plan-protocol.md` fixed to link rather than
  restate the three numbers (currently a Q1 duplication, P5-adjacent, not
  a Q2 problem). *Reason:* these are wire-format correctness bounds for a
  closed request/response grammar, not editorial terseness pressure — a
  shared config file would not know these numbers exist for the same
  reason it should not.
- **Per-adapter pacing constants** (`min_interval_ms`/`burst`/
  `cooldown_ms`, ~20 distinct values across `.orchflows/skills/
  super-research/scripts/super_research/adapters/*.py`) stay one owner per adapter file.
  *Reason:* each number is an empirically measured fact about one external
  service's actual rate limit (e.g. GitHub's 60/hr, documented inline with
  its source); centralizing them would not reduce duplication, it would
  just relocate facts that have exactly one correct place already.
- **Installer per-host concurrency ceilings** (`CODEX_MAX_THREADS=20`,
  `GROK_MAX_CONCURRENT=20`, `CLAUDE_MAX_TOOL_USE_CONCURRENCY=20`, `*_MAX_
  DEPTH=1`, `installer/foundation.py:99-105`) stay owned by
  `foundation.py`. *Reason:* already correctly single-owned in production
  code (`installer/hosts.py`'s `host_detection.py:251-252` reads them
  correctly); the actual defect (P6/P9) is eight *test* files retyping the
  values instead of importing them — a T7 fix, not a T3/config-file fix.
- **CI/toolchain version pins** (Python 3.9/3.13, Node 24 vs
  `reader/package.json`'s `>=20.19.0`, pnpm 10.32.1) stay owned by their
  respective manifest files (`pyproject.toml`, `reader/package.json`,
  `.github/workflows/checks.yml`). *Reason:* these are infrastructure pins
  consumed by tools outside this library's own config-loading path (GitHub
  Actions, Corepack, uv) — folding them into an orchflows-specific config
  file would not simplify anything, since the consuming tools would still
  need their native manifest format. The one real fix here is narrower:
  Node's floor (`>=20.19.0`) and CI's exact pin (`'24'`) should agree in
  form, and `pnpm`'s workflow-pinned version should read `package.json`'s
  `packageManager` field via Corepack instead of a hand-synced second
  literal — two small, local fixes, not a consolidation.
- **Serial-compat counts** (14 sentinels, 9 seams, 90s/100s timing)
  should be *derived*, not centrally configured: `tools/run_serial_
  compat.py`'s `EXPECTED_SENTINELS=14` should read
  `len(manifest["sentinels"])` from the regenerated
  `tests/serial_compat_manifest.json` rather than hardcoding the count
  that manifest happens to currently have, closing the loop B1.5's
  addendum-3 confirmed is (for now) accidentally consistent across three
  sites.

## Custom skills/workflows — the terseness mechanism

The Goal asks for a mechanism that presses a legitimately long custom
workflow toward terseness without a blanket cap squashing it, using
super-research (the one post-migration reference) as the worked example.
Two facts, checked directly:

- `.orchflows/skills/super-research/SKILL.md` is **740 words** — already
  well past every standing ceiling in `token-economy.md` §11 (workflow
  bodies 450 is the widest). It is not validated against any of them,
  because it is a project-ring custom item invoked manually, not a kernel
  skill, pack, or example-workflow — a category the current ceiling table
  simply does not cover. **[verified]**
- Its four `references/*.md` files total 1,166 lines
  (`evidence.md` 253, `internals.md` 240, `operating.md` 220,
  `protocol.md` 453) — detail pushed behind links, exactly the pattern
  `rules/token-economy.md` §6 prescribes ("everything else that survives
  §1... sits behind one link... placed at the call site"). **[verified]**

So super-research is not evidence that a raised cap is needed — it is
evidence the *existing* reference-delegation pattern already lets a
genuinely complex custom item stay large without bloating its `SKILL.md`
body, and it is currently unchecked by accident (no ceiling applies to
its tier at all), not by design. The mechanism to propose is therefore
not a new numeric exception field; it is closing that accidental gap with
the pattern the review already found working elsewhere in this same run
(T4/T8's "generate, don't author" principle, applied here as "declare,
don't default"):

1. Extend the config file from the section above with one more row: a
   ceiling for project-ring custom `SKILL.md` bodies, defaulted to the
   existing workflow-body number (450) so nothing currently compliant
   regresses.
2. A custom item that needs more declares its own budget as a frontmatter
   field (`budget: 750`) with a one-sentence justification comment beside
   it — the "declared, defended budget" the Goal names — and the
   validator checks the file against *that* number instead of the
   default, the same compare-stated-vs-actual pattern `tools/check_
   source_sizes.py`'s 500-line presumption already uses for code files
   (warn, never block, at the declared ceiling).
3. Review time is where "earns its place" gets judged: a custom item
   raising its own budget is exactly the kind of change a human or a
   review pass should read once, the same way `token-economy.md` §11
   itself says a ceiling only *falls* on review evidence — this is the
   mirror case, a ceiling *rising* on review evidence, with the same
   evidentiary bar.
4. The existing per-workflow `--bound "<= N tool calls"` pattern (already
   independently declared per-workflow in `example-workflows/drift-
   canary/SKILL.md:22,44`, `evolve/SKILL.md:26`, `self-improve/
   SKILL.md:35,46`, `super-research/SKILL.md:23`) is the same mechanism
   already working for *dispatch* bounds; step 2 above is that same
   pattern applied to *body-size* bounds, not a new invention.

Pre-migration custom workflows (browser-game, benchmaker, evolve, drift-
canary, renovate, skill-tournament, and the T3 `super-research` SKILL.md's
own divergences from this pattern) are counted as migration debt per
Details, not evidence against this mechanism — their vocabulary drift
(disposition/checkpoint/rung/tier/brief all carrying workflow-local senses
undocumented in `docs/vocabulary.md`, B1.4 supplement sub-scan 1) and
structural outliers (the BGW-TRACE traceability apparatus, `example-
workflows/browser-game/SKILL.md:7-20`) are pre-existing content this
review does not treat as design evidence.

## Trunk/leaf map

**Trunk** (mechanical core; every run depends on it; changes are rare and
high-cost): `rules/`, `contracts/`, `templates/host-block.md`,
`skills/kernel/orch-do/SKILL.md`, `skills/kernel/orch-judge/SKILL.md`,
the `tickets_*.py` dispatch/land/admission/store family, `scripts/
state_root.py`, `scripts/rings.py`.

**Leaf** (domain content; edited per-pack, per-workflow, per-tool, safe
to change without touching the trunk): each pack's `references/craft.md`
content specifics, `example-workflows/*/SKILL.md` and their `references/`,
`reader/` (a UI, not a mechanism), most of `tools/` (debugging and CI
utilities), `tests/`.

**Trunk logic sitting on a leaf, correctly:** the per-adapter pacing
constants and the search-plan protocol bounds (kept multi-owner above)
are domain facts that happen to look like trunk numbers but are actually
leaf-local — this placement is right and this review recommends no move.

**Trunk logic sitting on a leaf, incorrectly — belongs on trunk:**

- **P2's verification-scope clause** is a trunk rule (it governs every
  pack uniformly) with no trunk original stating it in prose — but the
  five leaf copies are not simply duplication to be moved: they are
  `scripts/tickets_assignment.py`'s live, machine-read dispatch anchors.
  T2 adds the trunk original to `rules/verification.md` without touching
  the leaf copies.
- **The env-var name and repo-root walk** (P3/P4) are trunk facts
  (`state_root.py` already correctly owns them) currently re-derived on
  20+ leaf files because the trunk file is unreachable from their position
  in the import order. T3 gives the trunk fact a genuinely reachable home.
- **The CI-topology sentence** (P10) is a trunk-adjacent fact (it
  describes `.github/workflows/checks.yml`, which is as close to trunk as
  CI configuration gets) currently hand-authored on two leaf tool
  docstrings. T8 generates it from the trunk source instead.

**Leaf logic sitting on trunk, incorrectly — belongs on a leaf:**

- `scripts/browser_game_validate.py` and `tools/validate_support/
  browser_game.py` (310 lines) are both entirely specific to one named
  example-workflow's domain (checkpoint/disposition/program-record
  vocabulary), living in `scripts/` and generic `validate_support/` —
  trunk territory — rather than under `example-workflows/browser-game/`
  or a browser-game-specific pack extension. B1.2's own finding notes
  this coupling is deliberate, not a stray leftover (six `tests/
  test_browser_game_*.py` files and the validator's `COMPOSITION_
  PROTOCOL_ALLOWLIST` wire it in on purpose) — but "deliberate" and
  "correctly placed" are different questions, and this review's answer to
  the second is no: a single-entry allowlist (`{"browser-game": "2026-08-
  28"}`, `tools/validate_support/structure.py:29`) naming one workflow
  inside a generic validator package is the textbook shape of leaf logic
  that migrated onto trunk because that was easier than building the
  extension point. No change proposed in this review (out of scope: a
  fix here is a genuine design project, not a mechanical move) — flagged
  as the clearest trunk/leaf inversion found, for a successor.
- `installer/managed_text.py:38-41`'s Grok limit-block renderer sits away
  from its sibling limit constants in `installer/foundation.py` "only
  because foundation.py is outside this ticket's write scope" — the
  file's own comment names a past ticket-authoring boundary, not a domain
  reason, as the cause. **Move `GROK_LIMIT_BEHAVIOR` back beside its three
  sibling `GROK_MAX_*` constants in `foundation.py`.** This is a one-line
  move with a self-documented, no-longer-applicable reason for its
  current placement — the cleanest "leaf fact stranded on the wrong file"
  finding in the review.

## Ranked change list — highest structural leverage first

1. **T1 — Fix `orch-judge/SKILL.md`'s Return clause.** Every judge
   dispatch currently reads a contradicted instruction; this is live
   behavior, not documentation, and the fix is a five-line edit to one
   file with contracts/shapes.json already stating the correct shape.
2. **T3 — One bootstrap-safe resolver for the env var and repo root.**
   Highest fan-out of any single fix (dissolves 12+ + 20+ = 32+ duplicate
   sites across scripts/, tools/, tests/, installer/, reader/ in one new
   ~20-line file — P3's corrected count), and it is the root cause of
   the review's two largest raw-count Q1 clusters.
3. **T9/T10 — The brick rename, executed as one commit, with the
   metaphor-test policy line landing in the same commit.** Already ruled
   for brick; this review's contribution is the complete occurrence map
   (assembled in Q3) and the explicit warning, grounded in the 2026-08-31
   friction log, that a split (per-branch or per-file) rename recreates
   the exact stale-constant failure mode already observed once.
4. **T2 — State the verification-scope law in `rules/verification.md`, additively.** Lowest
   cost, zero risk — a prose addition only. The five craft.md sentences
   stay exactly as written; they are `scripts/tickets_assignment.py`'s
   live dispatch anchors, not a visibility.md §3 violation to be closed
   by deletion.
5. **T6/T7 — One lifecycle-literal + phrase-anchor lint check.**
   Dissolves the single largest raw finding count in the review (P7/P8/P9
   together account for well over 100 individual Q1 lines across B1.2 and
   B1.5) with one new, narrowly-scoped validator check reusing
   machinery `tools/validate_support/duplication.py` already has.
6. **Numeric-limits config-file consolidation (the twelve-row table
   above).** Medium leverage, low risk, mechanical — eleven of the twelve
   numbers move from three files (token-economy.md prose, composition.md,
   common.py's dict) into one; the twelfth, `ARCHITECTURE.md`'s 925-word
   ceiling, is already enforced (see the table's own corrected verdict)
   and its number stays where `CEILING_RE` reads it. Two live defects get
   fixed as part of the same pass: the routing-block ceiling's complete
   non-enforcement, and the 60-vs-130 craft-budget contradiction.
7. **T8 — Generate the CI-topology sentence.** Small footprint (two
   files) but the single most concretely, independently reproducible
   defect in the entire review (P10) — worth fixing on confidence alone
   even though its blast radius is narrow.
8. **T4 — Section-text validation for cross-references.** Medium
   engineering cost (extends doclint's semantics, not just its coverage)
   for a defect class (P5) that is currently invisible by construction;
   ranked lower only because its current raw count (3 confirmed instances)
   is smaller than the clusters above.
9. **Custom-skill terseness mechanism (declared-budget frontmatter
   field).** Depends on item 6 landing first (it is the thirteenth row of
   the same config file); ranked here because it closes a real gap
   (super-research currently unchecked by any ceiling) but affects only
   one live custom item today.
10. **T5 — Close the retired-name roster's coverage gaps.** Lowest
    urgency: these are "what no longer exists" lists, so an incomplete
    roster produces a missed regression-test case, not a live-behavior
    defect the way items 1–9 do.
11. **Vocabulary documentation debt (ring/bundle/trust-ledger/surface/
    pin/seam/sentinel/shard/protocol/checkpoint entries).** Purely
    additive, no rename, no code change — the lowest-risk item on the
    list, ranked last only because it is also the lowest-leverage: it
    makes the library easier to search, not more correct.
12. **The `installer/managed_text.py` → `foundation.py` Grok-constant
    move**, and the trunk/leaf browser-game inversion flagged as a
    successor question rather than a mechanical fix. Smallest scope
    (one file each) and, for the browser-game case, explicitly deferred
    rather than resolved by this review.

## Seams — coverage gaps beyond the five stated lane surfaces

The five lanes' stated surfaces are B1.1 rules/docs/root, B1.2 scripts/,
B1.3 tools/installer/reader/CI, B1.4 packs/contracts/kernel/
example-workflows/ring, B1.5 tests/. Mapped against the tree's actual top
level, four more surfaces got no lane owner at all:

- **`templates/`** — one file, `templates/host-block.md`, trunk by this
  document's own trunk/leaf map above. It received only opportunistic
  coverage (P5's §6-vs-§3 citation, credited to B1.4) — the every-turn
  host-block surface had no enumerating lane.
- **`hosts/`** (4 files: `claude.json`, `codex.json`, `grok.json`,
  `profiles.md`) — in no lane's surface, though it is the canonical
  owner of launch facts (model/effort bindings) that `tests/
  test_dispatch_launch.py` independently hardcodes; the duplication was
  found from the test side, never enumerated from the owning side.
- **`benchmarks/`** — 1,051 files, in no lane's surface at all.
- **`.orchflows/`, the project ring** — nominally B1.4's surface, but the
  boundary was ambiguous even to the lane that owned it: this document's
  citations originally mixed `skills/super-research/` (a path that does
  not exist — `skills/` holds only `kernel/` and `workflows/`) with the
  correct `.orchflows/skills/super-research/` for the same tree, a
  pointer defect corrected throughout this repair.

Root non-doc files (`pyproject.toml`, `install.py/.cmd/.sh`,
`requirements-runtime.*`) are also outside any lane's stated surface,
though B1.1's "root" scope may have covered them informally. This is
disclosure, not a new defect claim: nothing above contradicts a finding
elsewhere in this document, it is simply unrepresented — and it is the
same gap class B-2's repair came from, a question spanning two lanes'
surfaces answered inside one and reported as a whole-tree negative.

## Cut log

No length budget was stated for this synthesis at the outset — a gap
this document should have named itself. Against roughly 1,700 raw lane
findings, the reduction to twelve Q1 patterns, five Q2 kinds, and one
Q3 term table dropped, deliberately: repeated per-file citations beyond
one representative site per pattern (P3–P9 above each cite a
representative subset of the many sites their source lanes actually
found, not the full count); and near-duplicate phrasing of the same
underlying fact across lanes, folded into the convergence note below
rather than listed per lane. Net-new: three clusters from the two
join-sanctioned supplements were read but, until this repair, not
reflected — the stale thirteen-probe count, the duplicate
`super-research` frontmatter name, and the vacuous retired-subcommand
test with its sibling dead test helpers. All three are restored above
(P12, P13). Nothing named here was cut for being wrong; everything cut
traces to a source lane's Report, and this log exists so a reader is not
left to infer that from the twelve-pattern surface alone.

## Coverage note

This synthesis draws on all five lanes' Reports, including the
join-sanctioned B1.4 supplement and B1.5's five addenda (the delegated
Explore-lane results that arrived after each ticket's own outcome had
closed) — see the Cut log above for the clusters that were read but
initially left unreflected, now folded in. A double-digit number of
claims were independently re-verified against the tree at commit
`58605b0f` directly (marked **[verified]** throughout this document):
among them, the orch-judge/shapes.json field-count contradiction (P1,
including reading both the SKILL.md text and `contracts/shapes.json`'s
actual field list directly), the "gate's row" clause's absence from
`rules/verification.md` and its two mechanical readers (P2), the
CI-topology matrix simulation (P10, plus reading `tools/preflight.py`'s
docstring text directly), the DESIGN.md/`common.py` craft-budget
contradiction (P12, cited again in the limits table), the
`ARCHITECTURE.md` ceiling's actual enforcement mechanism (the limits
table, corrected against P9), super-research's SKILL.md word count and
`references/` line counts (the custom-skill mechanism section), and the
env-var and probe-count undercounts folded in by this repair (P3, P12).
No finding here contradicts a source lane's own reading of the tree;
where two lanes converged independently on the same fact (e.g.
`ORCHFLOWS_STATE_HOME` found separately by B1.1, B1.2, B1.3, and B1.5),
that convergence is treated as its own form of verification and noted
in the relevant pattern above. This review made no changes to any file
outside itself, per Goal.
