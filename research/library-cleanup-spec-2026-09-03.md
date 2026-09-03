# Library cleanup — execution spec

2026-09-03. Executes the two reviews of this date (`REVIEW-2026-09-03.md`,
`REVIEW-2026-09-03-fable.md`) to their landable form, minus what the user
deferred. Run as a `team` frame from `research/library-cleanup-tickets/RUN.md`;
every unit is a code-pack `do` in its own worktree, landed on the run's
branch, judged, gate-green at every wave tip. Stop point: PR merged,
library reinstalled.

## 0. Decisions (closed)

1. **Contracts are ordinary editable documents.** The T0 hash-pin and
   supersession apparatus is deleted whole: `tests/pins.json`, `--pin`,
   `validate_pin_supersessions`, `_t0_shape`, every `T0 supersession
   record` paragraph and `## T0 supersession` section, and every sentence
   in law or docs that says a shape change "lands only through a
   supersession". What survives is the one structural check that earns
   its place: `contracts/shapes.json` rendered into each contract's
   generated table by `tools/render_shapes.py`, drift refused by
   `tools/regen.py`. A contract is changed by editing it and re-rendering.
2. **A retirement is a deletion.** Nothing retired is described in the
   present tense anywhere a reader loads. Git owns what was deleted. The
   `SUPERSEDED_EXECUTORS` refusal dict stays (it is a live refusal with a
   remedy), without its ninety-day expiry policy, which no data can fire.
3. **Out of scope, this run:** every body under `example-workflows/`, the
   shared `example-workflows/references/` bucket, and the browser-game
   machinery (`scripts/browser_game_validate.py`,
   `tools/validate_support/browser_game.py`, its tests and JSON). The one
   allowed touch inside a workflow body is the single sentence in
   `drift-canary` that points at `.orch/canary/` (U7 deletes the tree).
4. **Subtraction over addition.** Four additions are lawful, each because
   a declared oracle has no runner or a walked defect had no check:
   (a) the vocabulary consumer test in `tools/validate.py`; (b) the
   sheet-Lens-covers-every-named-pack check; (c) widening the link and
   documented-path checks to the human surfaces; (d) lifecycle rows whose
   actor is `caller` must name a routed subcommand. Nothing else is added.
5. **Prose the reader pays for is the target.** Where a unit chooses
   between deleting a copy and re-owning it, delete the copy; the owner is
   the file the vocabulary or ARCHITECTURE already names.
6. **The serial-compat lane is deleted only on evidence.** U7 first shows
   `tools/run_tests.py`'s boundary guard covers the nine seams the manifest
   sentinels cover; if it cannot, the lane stays as a manual command and U7
   reports it `limited`.
7. Fixtures that name retired executors are rewritten to `orch-do` /
   `orch-judge`, never deleted, where a test reads them.

## 1. Frozen goal

At one joined tip on this branch: the gate in section 5 passes; `grep -r
"T0 supersession" contracts/` is empty; `tests/pins.json` does not exist;
no file under `rules/`, `contracts/`, `docs/`, `skills/`, `packs/`,
`sheets/`, `hosts/`, `templates/`, `README.md`, `TICKETS.md`,
`ARCHITECTURE.md`, `DESIGN.md` names a callable, command, field, flag,
file or path that does not resolve in the tree; the law-text line count
(rules + contracts + manifest bodies, measured as the reviews measured it)
is below 2,400 and the frame journal records the number; `install.py`
reinstalls and `orchflows list` names every library item it named on
`main`.

## 2. Fixed names and shapes

- Kernel descriptions: `orch-do` — "Invoke when a ticket makes one
  artifact under a stamped pack." `orch-judge` — "Invoke when a ticket
  judges fixed artifacts under a stamped pack."
- `contracts/pack-signature.md` cells: `adapter`, `craft`. `## Stages`
  stays an optional craft section.
- `scripts/tickets_adapters.py`: three adapters — `git`, `document-tree`,
  `evidence-store`; fields `key`, `artifact_kind`, `establishes_isolation`,
  `deterministic_gate`, `workspace_strategy`, `commits_in_place`.
- Ticket frontmatter loses `independence`; `tickets_commands.VALUE_FLAGS`
  loses `--independence --cut-generation --correction-bound --result-file
  --verification-file --feedback-file --risks-file --handoff-file`.
- `hosts/claude.json` mode: `import`.
- `install.py`: `doctor [--quick]` is the one doctor spelling; no
  `--doctor`, no `--claude-adapters`.
- Rings: four — project, home, imports, lib — in every owner.
- Required checks in `AGENTS.md`: four (validate, run_tests, dry-run,
  diff --check) if U7 lands the lane deletion; five otherwise.
- Line widening: the link check and the documented-path check both grade
  `README.md`, `TICKETS.md`, `ARCHITECTURE.md`, `DESIGN.md`, `reader/docs`
  and `hosts`. The two trees join the directory rosters — `LINKED_MD_ROOTS`
  and `DOC_PATH_CHECKED_TREES`; the four root documents are files, so they
  arrive through `_linked_markdown_files`'s top-level glob and through
  `DOC_PATH_CHECKED_FILES` rather than through a roster whose consumers
  `rglob` and `is_dir`.

## 3. Units

### U0 — Delete the T0 pin and supersession apparatus

Delete `validate_pin_supersessions`, `compute_pins`, `write_pins`,
`_t0_shape`, `_historical_contract_text`, `_committed_pins` and `--pin`
(`tools/validate_support/lint.py`, `tools/validate.py`); `tests/pins.json`;
the pin tests (`tests/test_validator.py` pin cases,
`tests/test_validate_cases/pin_repin.py`); the supersession-marker handling
in `tools/render_shapes.py:188`. Delete every `T0 supersession record`
paragraph and `## T0 supersession` section in all eight contracts (457
lines), and the three "no compatibility aliases, dual parsing, or
migration mode" sentences (`bundle.md`, `sheet.md`, `work-item.md`).
Delete the supersession sentences in `docs/documentation.md` §2,
`docs/custom-workflow-authoring.md` §3, `docs/vocabulary.md` (**contract**
"Hash-pinned…", the whole **shape change** entry), `ARCHITECTURE.md` T0
line, and `README.md` "hash-pinned". `tests/test_ticket_protocol.py:85`
no longer partitions. `tests/test_validate_cases/sink_contracts.py` and
`contracts_and_names.py` lose their supersession assertions. Keep
`shapes.json` rendering and `regen`'s drift check untouched.

### U1 — Law text: contracts, rules, hosts, TICKETS, ARCHITECTURE

`contracts/work-item.md`: delete `## Review-stage ledger`, the
"Decomposition retired with orch-slice" sentence, the `tickets.py
instantiate` paragraph under `## Template and executor form`, the
`independence` half of its bullet, and "A multi-stage pack runs its
declared `stages`". `contracts/dispatch.md`: delete `review-invalid` and
the two tombstone paragraphs (`:140–158`). `contracts/result.md`: delete
`:44–50`. `contracts/worklog.md`: delete the `successors.md` paragraph.
`rules/verification.md`: rewrite §7 to its live sentence; delete §9;
renumber. `rules/visibility.md` §5: replace the cutcheck/`core.symlinks`
claim with what actually refuses a symlink (find it; if nothing does,
write "convention"). `rules/token-economy.md` §11: delete the 2026-08-16
sentence. `rules/delegation.md` §2: delete the launch-line inventory
sentence; §13: delete "A caller or policy may instead set another finite
positive bound." `hosts/profiles.md`: delete `## Running the terminal
required checks`. `TICKETS.md`: delete the cut-check item and the
"Ticket independence" item; renumber. `ARCHITECTURE.md`: delete the
ceiling history and every cutcheck sentence; one line each naming
`hosts/`, `benchmarks/`, `.orchflows/` as owners (decision 4 does not
cover this — it is a reword of the codemap's own coverage claim, net
negative with the deletions). No new sentence anywhere else.

### U2 — Vocabulary, DESIGN, custom-workflow-authoring, README counts

`docs/vocabulary.md`: delete **retired verb**, **decision gap**,
**assembly item**, **composition**, the tombstone halves of **critique**
and **gate**, the eight retired names in **routing shape**, the
`successors.md` sentence in **root ticket**, and the cutcheck citation in
**critical path** (rewrite to one sentence); trim **ladder / rung** to the
dispatch sense; **ad-hoc ticket** says `pending` at issue; **ring** says
four roots and names sheets; **bundle** names sheets. `docs/custom-workflow-authoring.md`
§Rings: four rings, imports named. `DESIGN.md`: delete "Why the named
tier is ticket-set templates"; delete the stale bullets and sentences at
`:39` (six shapes), `:58`, `:94`, `:138`, `:160` (Shape), `:192`
(consumer test), `:470` (four things), `:582`, and the "composition
contracts" road; keep only rationale for machinery that exists.
`README.md`: eight contracts; capitalise `:142`. Add the vocabulary
consumer test to `tools/validate.py` (decision 4a): every `- **term**`
entry has one consumer outside `docs/vocabulary.md`, `research/`,
`benchmarks/`, `.orchflows/` and `tests/`; error on zero.

### U3 — Ticket family: dead surface and the facade

Delete the `independence` field everywhere: `INDEPENDENCE_VALUES`,
`MINT_INDEPENDENCE`, `--independence`, `tickets_generations.py:25`,
`tickets_done.py:162,325`, `tickets_frame.py`, `contracts/shapes.json`
(`ticket_frontmatter`), then regen. Delete the eight `VALUE_FLAGS`
entries; delete `DRAFT_VALIDATE_USAGE`, `SEAL_USAGE`,
`GENERATION_SUBCOMMANDS` and the `--correction-bound` path
(`correction_decision` keeps bound 1 as a constant). Delete
`_pending_admission` (`tickets_issue.py:47`) and `actual_top_level`
(`workspace_git.py:120`). Trim `scripts/tickets.py` to the names something
references as `tickets.<name>` (census script in the review) and
`_sync_seams` to the five seams tests patch. Delete `scripts/cutcheck.py`,
its tests, its `installer/inventory.py` entry, and `tools/regen.py`/CI
references if any. `tickets_transitions.py`: the `issue`, `stamp`, `ready`,
`claim` specs carry the internal command that performs them as actor
(`tickets.py do|judge` / `dispatch`), and `render_lifecycle` refuses a
`caller` row whose event is not a routed subcommand (decision 4d).
`tickets_registry.py`: delete the expiry-policy comment. Reinstall
`tests/_retired_commands.py` against whatever internals remain.

### U4 — Packs, kernel bodies, adapters, sheets

Delete the `stages` and `assembly` cells: pack `SKILL.md` rows,
`packs_support.py` parsing, `PACK_SIGNATURE_CELLS`/`PACK_TYPED_CELLS`,
`shapes.json` `pack_cells`, `tickets_shapes.py`, `orchflows_scaffold.py`,
`contracts/pack-signature.md` cell table and the "One fact, one owner: the
retired…" paragraph, `docs/pack-authoring.md` step 6, the launch line "run
its declared stages in order" (`tickets_dispatch_launch_lines.py:191` —
becomes "Read your stamped pack's craft at …"). Delete
`Adapter.identity_form` and `conflict_semantics` and the tests asserting
them; delete the `git-plus-render` adapter; `orch-design-pack` declares
`adapter | git`. Delete the five "gate's row" bullets and
`CRAFT_SCOPE_ANCHOR`/`_craft_scope`/`craft_scope` plumbing; the standing
prompt line is the one owner (`rules/verification.md` §8). Reword
`orch-design-pack/references/craft.md:88` to pointers. Kernel descriptions
per section 2; `orch-do/SKILL.md` drops its Details-deviation sentence
(`work-item.md` owns it; the prompt carries it). `sheets/html-dossier`
`packs: [orch-content-pack]`. Add to `tools/validate_support/sheets.py`:
every pack a sheet names has a `### <kind>` entry (decision 4b).

### U5 — Reader and the human surfaces' oracles

Delete `manifest_paths`, `valid_host_headers`, `active_claims`,
`transcript_state`, `status_presentation`, `project_observe`,
`project_workflows`. Delete `reader/docs/modularization.md` and the plan
prose of `reader/docs/workflows.md` down to what describes the live
catalog; delete `experience_projection.py:14,26` and any test pinning
either file. `reader/docs/platform.md`: route table equals
`create_application().routes`; "64"; `reader/scripts/ui.py`. `README.md:43`
the same path. Fix `reader/docs/workflows.md:7`'s link. Delete eslint:
`package.json` `lint` script, `eslint` and `typescript-eslint`
devDependencies, `eslint.config.js`, the two assertions in
`test_reader_extraction.py`; regenerate the lockfile and confirm
`verify-build` reproduces the committed dist. Rewrite
`tests/fixtures/ui/run-*` executors to `orch-do`/`orch-judge`. Widen
`LINKED_MD_ROOTS` and `DOC_PATH_CHECKED_TREES` per section 2 (decision 4c)
and fix what they then find.

### U6 — Installer

Remove the `scope` parameter from `installer/planning.py`,
`application.py`, `presentation.py`, `foundation.py` and `install.py`'s
`build_plan`/`print_plan`/`apply_plan`; `uninstall.py` keeps its own
project-root argument. `hosts/claude.json` mode `import`;
`upsert_import_line` loses its legacy-block strip and the
`migrated-from-block` action. One doctor spelling. Delete
`--claude-adapters`, `CLAUDE_ADAPTER_SETS`, `SHARED_ADAPTER_NAMES`,
`_mints_claude_adapter`, `tools/live_routing_bench.py` and
`tools/live_routing_bench_support/`, `benchmarks/routing/`, their tests,
`README.md`'s `--claude-adapters` paragraph, and `DESIGN.md:131`'s
benchmark sentence. `install.py --dry-run` plans the same 361 entries
before and after.

### U7 — Tools and tests

Delete `tools/live_claude_profiles.py`, `tools/live_codex_profiles.py`,
`tools/live_sweep_e2e.py`, `tests/test_live_harnesses*`;
`tools/suite_check.py`, `tests/test_suite_check*`, its mentions in
`docs/documentation.md:138` and `tests/__init__.py:12`;
`scripts/migrate_state*.py`, `tests/test_migrate_state*`, the inventory
entry; `scripts/isolate.py`, `scripts/fixture.py`, their tests;
`.orch/canary/` and the one `drift-canary` sentence (decision 3).
Serial lane, under decision 6: show `run_tests.py` `guarded_state`
covers cwd, environment, event-loop, import-path, logging, module-cache,
monkeypatch, warnings, threads; then delete `tools/run_serial_compat.py`,
`tools/serial_manifest.py`, `tests/serial_compat_manifest.json`,
`tools/serial-compat-policy.md`, `.github/workflows/serial-compat.yml`,
`tests/test_serial_compat*`, `tests/test_serial_manifest.py`; `AGENTS.md`
names four checks; `docs/vocabulary.md` drops **sentinel**, **shard** and
the second sense of **seam**; `tools/run_required.py` runs four.
`tests/test_installer_cases/support.py`: `_build_private_runtime` is
patched to a copy of one template built by a single case that is skipped
unless `ORCHFLOWS_LIVE_PYPI=1`; the suite makes no network call
otherwise. The ten tests reading production `.py` source as text assert a
shape (a name, a count, a set) or are deleted.

### U8 — Prose inside code

Across `scripts/`, `tools/`, `installer/`, `reader/scripts/`: docstrings
and comments hold the module's opening contract, invariants, ordering
constraints, and why-not-the-obvious — `packs/orch-code-pack/references/craft.md:96`
— and nothing else. Delete change narrative, dated evidence, run-local
ticket ids (`U13(c)`, `S7(a)`, `F4`, `A2`, `W4a`, `PJ-*`, `B1.*`),
"used to"/"retired" histories, and `orchflows_check.py:26–27`'s home-ring
citation. Bound: no module's prose share above 30%; `scripts/` total
below 12%. Behaviour unchanged: the suite is the oracle.

## 4. Waves

| wave | units | waits on |
|---|---|---|
| 1 | U0 | base |
| 2 | U3, U4, U5, U6, U7 | U0 |
| 3 | U1, U2 | wave 2 (prose describes landed code) |
| 4 | U8 | wave 3 |
| 5 | gate | U8 |

Wave 2 touches disjoint files except `contracts/shapes.json` (U3 and U4
both edit it; U4 lands second and rebases its rendering) and
`docs/vocabulary.md` (U7 deletes three entries; U2 owns the rest, later).

## 5. Gate

At the joined tip, once, outside every child:

    uv run --no-project python tools/run_required.py --no-cache
    uv run --no-project python install.py --dry-run
    git diff --check
    grep -r "T0 supersession" contracts/    # empty
    test ! -e tests/pins.json

Then reinstall, `orchflows sync`, `orchflows list` (every library item
still named), and the law-text count recorded in the frame journal. One
content-pack `judge` over `rules/`, `contracts/`, `docs/vocabulary.md`,
`DESIGN.md` against decision 2, or `unjudged: <reason>`.

## 6. Deferred

Everything under `example-workflows/` (the reviews' Thread 5 / Thread D
and E), the shared references bucket, browser-game's carve-out, and the
`research-acquire` ring placement. Successor spec after reinstall.
