# Library review — 2026-09-03 (second pass)

## Review header

- Reviewed identity: `git-tree:8b7557179db9` at `main` `468dbdc9` (PR #171
  merged), the same tree `REVIEW-2026-09-03.md` graded. Independent pass:
  its own lanes and its own measurements; convergence with that report is
  noted at the end, not assumed.
- Scope: every tracked tree except `benchmarks/benchmaker/cases/**`,
  `research/`, and test fixtures — with two additions the first pass
  skipped: the full text of every contract, craft, sheet and workflow body,
  and the `scripts/tickets_*` family read at source rather than by census.
- Law-text line count: **2,894** physical lines (`rules/` 537 across 9
  files; `contracts/` 1,573 across 8; 784 body lines across 20 manifests
  after the closing YAML delimiter). Delta since 2026-08-26: **+1,313**.
- Validator state: **PASS** (0 errors, 18 warns).
- Test state: **PASS**, 97 modules, 2,328 tests; one red in seven runs
  from `tests.test_installer_shared` building a real venv against
  pypi.org (Thread 6).
- Production Python: 45,501 lines. Test Python: 56,628 lines (1.24 : 1).
  Prose inside `scripts/`: 21% of lines are docstring or comment.
- No fixes applied.

## Root-cause threads

Six threads. Each names one cause, one owner, one remedy from
**delete > merge > reword > move > add**, with evidence at `file:line`.

---

### 1 — Law that describes machinery the tree does not contain

**Owner:** the file that makes each claim; the two oracles that let them
through. **Remedy: delete** the claims; **reword** two oracles' scope.
Planned delta **−60** law lines, **+15** validator lines.

`docs/documentation.md` law 6: *"Write 'X is refused' only where a script
or test refuses X."* Graded per claim against the source:

- **`rules/visibility.md:20`** — *"`scripts/cutcheck.py` is the instrument —
  one `symlink-in-tree` finding per entry — and it clones the copy oracles
  run in with `core.symlinks=false`."* `scripts/cutcheck.py` (78 lines)
  contains no symlink code. The string `symlink-in-tree` occurs in exactly
  one file in the repository: that rule. So does `core.symlinks`. A rule
  naming its instrument, and the instrument does not do the thing.
- **The same script has four owners describing four different bodies.**
  `ARCHITECTURE.md:111` — "owns cut-defect detection over issued ticket
  sets"; `:50–53` — an import law for it. `TICKETS.md:166` — "accepted
  when cutcheck.py exits 0. Once a unit dispatch opens, cut correction is
  refused." `docs/vocabulary.md:456` — reads critical path "from
  `scripts/cutcheck.py`'s `graph` block (classes `critical-path`,
  `level-width`)". The actual script: duplicate-id, ticket-shape,
  dangling-dependency, dependency-cycle — no graph block, no critical path,
  no symlinks. It accepts `--baseline` and `--lib` and ignores both
  (`cutcheck.py:56–57`: "host routing value; structural validation is
  revision-independent"). No live command calls it; `tickets_emission.py`
  already grades dependency shape at emission. Since W4a retired issued
  cuts, nothing produces the ticket set it was written to read.
- **`contracts/dispatch.md:110`** — "Dispatch refuses `review-invalid` when
  the ticket's review ledger does not admit this lane." Zero occurrences in
  `scripts/`. I checked every other refusal code named in `dispatch.md` and
  `TICKETS.md` (fourteen); each resolves to code. This one names a ledger
  the same contract retires forty lines later (`:154`).
- **`contracts/worklog.md:38`** and **`docs/vocabulary.md:210`** —
  `successors.md`, "the durable successor plan … a planning `do` is its
  sole writer; the driver reads it once `tickets.py land` reports an empty
  frontier." Zero occurrences in `scripts/` or `reader/scripts/`. A
  contract paragraph for a file nothing writes or reads.
- **`docs/lifecycle.md`** — "Generated … from the executable declarations
  … the public lifecycle view cannot acquire a second, hand-maintained
  state machine." Six of its 92 rows carry events `issue`, `stamp`,
  `ready`, `claim` with actor `caller`. None is a subcommand
  (`tickets_commands.py:SUBCOMMAND_USAGE`); `tests/_retired_commands.py`
  reaches them "at their internals" because the routes are gone. The
  `STAMPS` table (`tickets_transitions.py:59`) has one caller,
  `tickets_seal.py:134`, itself reachable only through the retired
  `draft-validate`. The rendered view is faithful to declarations that are
  themselves stale.
- **`docs/vocabulary.md:217`** — ad-hoc ticket: "`ready` at issue."
  `tickets_issue.py:205,255` writes `status: pending`. The 2026-08-26
  review's first thread named this exact sentence. It is still there.
- **`README.md:43`** and **`reader/docs/platform.md:13`** — "start it with
  `uv run --no-project python scripts/ui.py`". There is no
  `scripts/ui.py`; the CLI is `reader/scripts/ui.py` (`platform.md:69`
  says so). The first command a new user is told to run does not run. The
  documented-path oracle cannot see it: `tools/validate.py:164` sets
  `DOC_PATH_CHECKED_TREES = _INSTALLED_LIB_DIRS`, so README and
  `reader/docs/` are outside it.
- **`reader/docs/platform.md:78–87`** — the route table `ARCHITECTURE.md`
  calls "the complete boundary" lists ten `/api/v1` routes. The live
  application (`ui_api.create_application()`) serves fifteen: the four
  `/api/v1/workflows*` routes and `/api/v1/views/{view}` are absent from
  the table, as are the browser routes `/observe` and `/workflows*`.
  `:138` says the view manifest "declares 62 deterministic identities";
  `view-manifest.json` holds 64.
- **`DESIGN.md:192`** — the craft is bounded by "a closed consumer test
  that makes an unconsumed term a defect, both owned by the cell's
  definition in `contracts/pack-signature.md`." That contract contains no
  consumer test (its only "consumer" is the generated-shape validator
  wording).

The two oracle gaps are one line each: widen `DOC_PATH_CHECKED_TREES` to
the human surfaces, and add to `render_lifecycle` the rule that a
`caller`-actor row names a routed subcommand.

---

### 2 — Sealed shapes, public flags and tracked fixtures with no consumer

**Owner:** `contracts/work-item.md` (`independence`), `scripts/tickets_commands.py`,
`scripts/tickets.py`, `.orch/canary/`, `benchmarks/routing/`.
**Remedy: delete.** Planned delta **−2,300** lines, one T0 supersession.

- **`independence` is sealed and dead.** `tickets_issue.py:43`
  `INDEPENDENCE_VALUES = ("gate", "checker")`; `:281` defaults a
  hand-written ticket to `"checker"` — the value `rules/verification.md:27`
  says "no longer names a distinct path"; `tickets_mint.py:89` writes
  `"gate"` for every minted callable; `tickets_generations.py:25` folds
  the field into the assignment digest. No code branches on the value.
  Two tickets with identical Goal, Context, Details and executor differ in
  seal by a field with no meaning, and the T0 shape table
  (`work-item.md:244`) pins it.
- **Eight dead flags in `VALUE_FLAGS`** (`tickets_commands.py:98–110`):
  `--result-file`, `--verification-file`, `--feedback-file`,
  `--risks-file`, `--handoff-file` — the five retired report headings
  `platform.md:109` calls "the earlier contract's" — occur nowhere else in
  `scripts/`; `--independence` (above); `--cut-generation` and
  `--correction-bound` reach only the retired `draft-validate`/`seal`
  (`tickets_seal.py:49–50,264–269`). `correction_decision`'s bound
  (`tickets_generations.py:203`) is therefore unreachable from `do`,
  `judge` or `frame-open`, and `rules/delegation.md` §13's "a caller or
  policy may instead set another finite positive bound" has no door.
- **The `tickets.py` facade re-exports 185 names; 25 are ever referenced
  as `tickets.<name>`** (census over every `.py` in the tree). Its
  `_sync_seams` (`:276`) re-points 25 seams into helper modules; tests
  patch 5 of them (`msvcrt`, `datetime`, `_cmd_ready`,
  `_cmd_dispatch_open`, `_write_identity`). 160 private re-exports and 20
  sync lines serve nothing. The facade exists because the family is
  importable two ways — 45 modules carry 85 `if __package__:` blocks and
  66 `except ImportError:` branches — and a test patching the package
  object must reach the flat one. That dual layout is the cause; the
  facade is its symptom.
- **`.orch/canary/`** — 23 tracked files, 1,426 lines, last touched
  2026-08-31. Its README (`:10–11`) says to run it "through `orch-frontier`
  (per `skills/engines/orch-frontier/SKILL.md`)"; one golden item is
  `canary-tdd-micro`; `single/inputs/orch-fixture.SKILL.md` and its
  tickets name `orch-tdd` and a checker pass. Every one of those retired.
  `golden.json` has no consumer. The one test naming the tree
  (`tests/test_validate_cases/sink_law.py`) uses its *path*. The
  `drift-canary` workflow points at it (`SKILL.md:23`).
- **`tests/fixtures/ui/run-*`** — 18 fixture tickets; every `executor:` is
  `orch-tdd` (13) or `orch-verify` (5). The reader's rendered contract,
  smoke, and 64 view-manifest identities are frozen over tickets no
  command can dispatch.
- **The routing benchmark apparatus.** `benchmarks/routing/cases.json`
  routes 32 prompts to `answer`, `single`, `graph`, `spec` — all retired
  lanes; its README says it "decides SPEC §7.2" (no such document in the
  tree). `DESIGN.md:131` records the decision as closed on 2026-08-16:
  "Claude keeps all skill adapters." What survives the closed experiment:
  `tools/live_routing_bench.py` (186), `install.py --claude-adapters
  {all,four}`, `SHARED_ADAPTER_NAMES` and `_mints_claude_adapter`
  (`installer/planning.py:101–113`, whose docstring says the flag exists so
  "the routing benchmark needs the two installs to differ in this one
  surface alone"), and a README paragraph. `four` mints two.
- Minor, same cause: the kernel descriptions (`orch-do:3`, `orch-judge:3`)
  state what the skill is, not when to invoke it — `rules/token-economy.md`
  §8 — while every pack and sheet ends "Stamp when …" as the law asks.

---

### 3 — One fact, several owners, held together by string anchors

**Owner:** each fact's rightful file; `scripts/tickets_assignment.py:62`.
**Remedy: merge** and **delete** copies; make two anchors checked.
Planned delta **−40** law lines, **+20** validator lines.

- **The Details-deviation rule has three live owners and one tombstone.**
  `contracts/work-item.md:26` ("deviation is pre-authorized where following
  Details would break Goal, reported with the observation that forced
  it"); `skills/kernel/orch-do/SKILL.md:15–16`; the launch prompt,
  `scripts/tickets_dispatch_launch_lines.py:138–139`; and again inside a
  supersession record at `work-item.md:388`. Every `do` dispatch carries
  it twice into the child's context — once in the prompt, once in the
  kernel body the prompt tells it to read.
- **The verification-scope law is copied five times and extracted by
  substring.** `rules/verification.md` §8 owns it. Each pack's craft
  restates it as a `## Stages` bullet (`orch-code-pack:115`,
  `orch-content-pack:108`, `orch-data-pack:115`, `orch-design-pack:124`,
  `orch-research-pack:107`). `tickets_assignment.py:152–177` then finds
  the bullet by searching for the literal `"gate's row"`
  (`CRAFT_SCOPE_ANCHOR`, `:62`) and, when absent, silently substitutes a
  standing line. Nothing validates that a craft still carries the anchor.
  Three prose anchors of this class exist: `"gate's row"` (silent
  fallback), the `sub-questions` heading (`tickets_mint.py:117` — the
  well-formed instance: the craft states the form and the door refuses
  loudly), and the `shape:` journal prefix. The first should either be the
  third's shape or be deleted with its five copies.
- **"No compatibility aliases, dual parsing, or migration mode"** —
  `contracts/bundle.md:75`, `sheet.md:102`, `work-item.md:271`, verbatim;
  five contracts do not carry it. The fact is already
  `docs/documentation.md` §2's and the vocabulary's **shape change**.
- **Three rings or four.** `docs/custom-workflow-authoring.md:11`: "one of
  three rings"; `rules/composition.md:69` §14: three; `docs/vocabulary.md:136`:
  "one of four fixed lookup roots — project, home, imports, lib";
  `scripts/rings.py:49`: `RINGS = ("project", "home", "imports", "lib")`.
  The same two vocabulary entries (`:136`, `:139`) list the item kinds a
  ring or bundle holds as skill/pack/workflow; the authoring doc says four
  kinds. Sheets are missing from the retrieval API's own definition of
  where they live.
- **Law that depends on package internals.** `ARCHITECTURE.md`: "a rule
  never depends on package internals." Eight clauses cite a script by path
  — `rules/visibility.md:20,35,43,46,47`, `delegation.md:28`,
  `token-economy.md:64`, `verification.md:38`. `delegation.md:28` goes
  further and enumerates the launch renderer's line inventory ("one line
  per sheet … the applied skill's identity and kernel-contract lines … that
  skill's interpreter line … each rendered by
  `scripts/tickets_dispatch_launch_lines.py`") — a rule restating a
  module's function list.
- **A craft contradicts its contract.** `packs/orch-design-pack/references/craft.md:88`:
  "Each view item repeats verbatim its identity list, its render, capture
  and diff commands, its accessibility bar and design language, and the
  standards owner pointer." `contracts/work-item.md:18`: Context carries
  facts "as pointers rather than inlined copies."
- **Wrong owner.** `hosts/profiles.md:32` "## Running the terminal
  required checks" — two sentences of verification law in the file that
  binds roles to models.
- **A sheet whose Lens binds nothing for one of its packs.**
  `sheets/html-dossier/SHEET.md:4` `packs: [orch-content-pack, orch-design-pack]`;
  its `## Lens` has `### doc` only. The design pack's kind is `git`.
  `tools/validate_support/sheets.py:195–218` checks entries ⊆ kinds, never
  that each named pack's kind has an entry, so stamped beside the design
  pack the sheet is inert and no check says so.
- Small: `install.py` reaches doctor three ways — positional `doctor`,
  `--doctor`, `--quick`; `README.md:18` prescribes `doctor --quick`, the
  host block `install.py doctor`.

---

### 4 — Rationale and history that outlived what they explain

**Owner:** `DESIGN.md`, `contracts/*.md` tombstone sections,
`docs/vocabulary.md`, `scripts/*` docstrings. **Remedy: delete.**
Planned delta **−350** doc lines, **−300** code-prose lines.

`DESIGN.md` is the largest single owner in the tree (5,939 words) and is
stratified by date rather than by the current design. Read cold, a reader
gets three eras stacked, each asserting the present tense:

- `:39` "N workflows, M packs, and H hosts meet in six data shapes" — eight
  contracts.
- `:58` "**Compositions are the stdlib.** A named workflow is a data file
  — steps, edges, invariants, done check" — a workflow is prose.
- `:94` "Custom workflows instantiate from compositions" — `instantiate`
  retired.
- `:138` the loop engine "since absorbed into the driver as the ticket
  `loop` field" — `rules/loops.md`: "no loop engine and no loop marker."
- `:160` craft is "**Vocabulary** and **Shape**" — Shape retired into Lens.
- `:470` "the four things a model still has to decide: freeze a root, cut
  it, build a unit, challenge one" — nine lines later, `:479`: "**Two
  callables, not four.**" The file contradicts itself across one page
  boundary.
- `:582` "executors are the domain leaves a pack binds by exact name" —
  packs have bound no executor since the signature supersession.

The contracts carry the same strata inline, above their supersession
records: `contracts/work-item.md:145–160` (`## Review-stage ledger`,
entirely about retired fields and a retired command), `:177–181`
("Decomposition retired with orch-slice, its only minter (W4a)"),
`:200–205` (`tickets.py instantiate` "retired"); `contracts/dispatch.md:140–158`
(two paragraphs on `--findings-file`, `.gate.critique.<lens>`, `review_v1`);
`contracts/result.md:44–50`. `rules/verification.md` §§7, 9 are the same
history again.

`docs/vocabulary.md`, "the retrieval API", carries: **retired verb** (`:66`,
restating `SUPERSEDED_EXECUTORS`); **composition** (`:103`, "surviving as
the reader's projection type" — `reader/scripts/ui_workflows_catalog.py:60–64`
reads both homes as workflow skills and `reader/docs/workflows.md:7` says
the type retired); **assembly item** (`:263`, nothing mints one);
**decision gap** (`:265`, "the stamped slicing"); **critique** (`:320`,
half tombstone); **gate** (`:328`, nine of thirteen lines are "Retired:");
**ladder / rung** (`:411`, fifteen lines, ten disambiguating a
benchmark-only sense); **critical path** (`:453`, a cutcheck block that
does not exist); and the routing-shape entry's eight retired names
(`:235–238`).

The code carries the same habit. `scripts/` is 21% prose by line;
`tickets_emission.py` 54%, `tickets_project.py` 54%, `state_root.py` 44%,
`tickets_dispatch_launch_lines.py` 41%. Much of it is change narrative
keyed to identifiers that resolve nowhere in the tree — 26 docstring
citations of run-local ticket ids (`U13(c)`, `S7(a)`, `F4`, `A2`, `W4a`,
`PJ-28`). `scripts/orchflows_check.py:26–27` justifies a rule by "the home
ring's own `super-research` body is 672 words" — the author's machine
state, cited in library code (it is 700 today). The code craft's own bar
(`orch-code-pack:96`): "Comments state only what code cannot: the module's
opening contract, invariants, ordering constraints, why-not-the-obvious."

---

### 5 — Gallery workflows that do not obey the law they ship beside

**Owner:** each `example-workflows/*/SKILL.md`. **Remedy: move** one skill,
**reword** three bodies, **delete** the shared references bucket into its
owners. Planned delta **−30** body lines, **0** net for the move.

- **`super-research/SKILL.md:18`** dispatches `--skill research-acquire`.
  That skill lives only at `.orchflows/skills/research-acquire/` — this
  repository's project ring. `orchflows list` run from `%TEMP%` against
  the live install does not list it; the workflow's first call refuses for
  every installing user. `rules/visibility.md` §2: a shared package never
  names a project package. No check catches a `--skill` argument inside a
  fenced block.
- **`skill-tournament/SKILL.md:27`** opens the nested benchmaker frame as
  `frame-open <run> --parent <frame> --goal-file <benchmark-goal>` — no
  `--workflow benchmaker`, no shape. `tickets_shape_line.py:68–84`
  (`shape_for`) returns `(None, None)` for any parented frame, so the
  journal records no plan and the body's own law ("a saved workflow's root
  `frame-open` names `--workflow <name>`") is unenforced below the root.
  The same body invokes `evolve` the same way.
- **`benchmaker/SKILL.md`** has one fenced `tickets.py` command; every
  other body has two to four. Its three making calls and three judging
  calls are prose ("`do` with `--pack orch-research-pack`") — a driver
  copies commands from every other gallery entry and reconstructs them
  here.
- **`example-workflows/references/`** is a shared bucket for four owners.
  `rules/visibility.md` §4: a `references/` file "belongs to one package
  and is public only when its owner names the exact local path in its own
  body." `evolve-generation.md` is named by no workflow body — only by
  `reader/docs/workflows.md:45`, `tests/test_search_plan.py:28`, and
  `tests/test_static_tree_invariants_cases/benchmark_architecture.py:14`,
  which still spells the directory `COMPOSITIONS / "references"`.
- **`drift-canary/SKILL.md:20–24`** re-issues golden items "under a nested
  run of its own beneath `.orch/canary/`" — runs live in the user-scope
  sink, never inside a repository (`rules/visibility.md` §6) — and files
  verdict deltas "as one friction entry per named divergence."
  `rules/improvement.md` §1 defines friction as observed obstruction; a
  canary delta is a measurement, and writing it into the friction stream
  feeds the self-improve harvest signals that are not friction.
- **`browser-game/SKILL.md`** — 23 of 82 lines are `<!-- BGW-TRACE -->`
  comments serving a validator carve-out (`structure.py:29`) the
  workflow-admission law names as its "sole exception". The first pass
  measured the footprint; the point here is narrower: it is the one
  gallery body a driver cannot read without wading through validator
  anchors.

---

### 6 — The test apparatus outweighs its subject and is partly ungoverned

**Owner:** `AGENTS.md` required checks; `tools/run_serial_compat.py`,
`tools/suite_check.py`; `tests/test_installer_cases/support.py`.
**Remedy: delete** two harnesses, **reword** one fixture.
Planned delta **−7,000** lines (of which 5,804 is one committed manifest).

- **1.24 test lines per production line**, and the machinery to run them
  is 3,143 lines across nine tools (`run_tests` 515, `run_serial_compat`
  519, `affected_tests` 515, `suite_check` 347, `verify_at` 318,
  `run_required` 309, `preflight` 308, `run_tests_scope` 168,
  `serial_manifest` 144) plus a committed `tests/serial_compat_manifest.json`
  of 5,804 lines, a nightly workflow, and a policy document.
- **The serial lane guards a seam the parallel runner already guards.**
  `.github/workflows/checks.yml:14–16`, in the repository's own words:
  "The serial compatibility oracle repeats the regression suite; the
  parallel runner now rejects residue at the module boundary itself."
  `AGENTS.md` still lists it as one of the five checks that decide the tip,
  and `serial-compat.yml` runs both its modes nightly on two OSes.
- **`tools/suite_check.py`** (347 lines, plus `tests/test_suite_check*`):
  named by `docs/documentation.md:138` as a convention owner and by
  `tests/__init__.py:12`; invoked by nothing.
- **Ten test files read production `.py` source as text** —
  `tests/test_workspace.py:73,79`, `test_events.py:401`,
  `test_isolate.py:389`, `test_validate_cases/sink_contracts.py:174`,
  `test_validate_measures_cases/row.py:270`,
  `test_workspace_cases/candidate_cases.py:634`, and three under
  `reader/tests/`. The code craft's own rule (`orch-code-pack:101–107`):
  checks pin shapes, never sentences; a check reading an owner file reads
  a stable anchor.
- **`tests/_retired_commands.py`** keeps `stamp-generation`,
  `draft-validate`, `seal` and `ready` runnable "at their internals" so
  fixtures can walk a lifecycle `do` cannot. The commands are dead on the
  surface, alive underneath, with a test-only door — which is why Thread 2's
  `--cut-generation`/`--correction-bound` and Thread 1's `STAMPS` survive.
- **`tests/test_installer_shared`** builds a real private runtime with
  `pip install --require-hashes` against pypi.org
  (`installer/runtime.py:189–201`, `support.py:85`), five times per suite
  run, 87 s of a 113 s wall. Reproduced red once in seven runs on a
  transient index error. A required check that answers to a third-party
  index is not deterministic.

---

## Net delta

Applying every thread: roughly **−500** law and doc lines (Threads 1, 3, 4),
**−2,300** tracked fixture, benchmark and flag lines (Thread 2), **−7,000**
test-apparatus lines if the serial lane and `suite_check` go (Thread 6),
against **+35** added validator lines (Threads 1, 3) and one `move` (Thread
5). The only `add`s are oracle scope: two one-line widenings and two small
checks (lifecycle actor rows name a routed subcommand; a sheet's Lens
covers every pack it names). Each closes a gap a finding above walked
through.

## The five safest deletions, independent of any defect

1. **The `independence` frontmatter field**, `INDEPENDENCE_VALUES`,
   `MINT_INDEPENDENCE`, and `--independence` (`tickets_issue.py:43,281`,
   `tickets_mint.py:89`, `tickets_generations.py:25`, `tickets_commands.py:103`).
   Ablation: remove, `--pin` with one supersession record, run the suite.
   No branch reads the value; the digest change is the only effect.
2. **The eight dead `VALUE_FLAGS` and `tickets_seal.GENERATION_SUBCOMMANDS`
   with its two usage strings.** Ablation: grep each flag across `scripts/`
   — five occur nowhere else; three reach only `tests/_retired_commands.py`.
3. **`.orch/canary/`** (23 files) and the sentence in `drift-canary` that
   points at it. Ablation: `tests/test_validate_cases/sink_law.py` names
   the path only; run it after `git rm`.
4. **The 160 unreferenced facade re-exports and 20 unpatched `_sync_seams`
   lines in `scripts/tickets.py`.** Ablation: the census in this report —
   every `.py` in the tree, every `tickets.<name>`, `patch.object(tickets,
   …)` and `from … tickets import` — then the suite.
5. **`benchmarks/routing/`, `tools/live_routing_bench.py`,
   `--claude-adapters`, `SHARED_ADAPTER_NAMES`, `_mints_claude_adapter`.**
   Ablation: `DESIGN.md:131` records the decision the benchmark existed to
   make; `install.py --dry-run` before and after plans the same 361 entries
   under the default.

## Standing inventory — invariants only review enforces

- That a rule's "X is the instrument for Y" names code that does Y
  (Thread 1: `visibility.md` §5).
- That a contract's refusal code exists in `scripts/` (Thread 1:
  `review-invalid`).
- That a contract's named file has a writer (Thread 1: `successors.md`).
- That a sealed frontmatter field has a reader (Thread 2: `independence`).
- That a `VALUE_FLAGS` entry has a consumer (Thread 2).
- That a craft still carries the substring the launch prompt extracts
  (Thread 3: `"gate's row"`).
- That a sheet's `## Lens` covers every pack it names (Thread 3).
- That a nested `frame-open` in a saved workflow names `--workflow`
  (Thread 5).
- That a `--skill` argument in a workflow body resolves in the library
  ring (Thread 5).
- That a human-surface command (`README.md`, `reader/docs/`) names a file
  that exists (Thread 1).

## Meta-analysis

Every thread here is the same defect at a different altitude: **the tree
keeps its own past in the present tense.** A rule names an instrument that
was hollowed out (1). A sealed field, eight flags, a facade, a fixture tree
and a benchmark keep the shape of the code that used them (2). Copies of a
law survive because nothing owns the copy (3). The rationale file and the
vocabulary carry every era as if all were current, and the code's own prose
does the same with ticket ids that mean nothing outside the run that minted
them (4). A gallery body reaches for a skill that lives in the author's
checkout (5). And the test layer — larger than the library — is where the
retired commands are kept alive for the fixtures that need them (6).

The first pass located the ratchet that prevents pruning contract history.
This pass finds that the ratchet has siblings everywhere the library
records a retirement: the retirement is written *beside* the thing rather
than *instead of* it. `tickets_registry.py`'s expiry policy is the tell — a
ninety-day tombstone horizon that no data can ever fire.

**The single move that closes the most threads:** adopt, in
`docs/library-review.md`'s constitution, one sentence — *a retirement is a
deletion, and git owns what was deleted* — and let `tools/validate.py`
enforce its cheapest corollaries: no `.md` under `rules/`, `contracts/`,
`docs/`, `skills/`, `packs/`, `sheets/` or `example-workflows/` names a
callable, command, field, file or path that does not resolve in the tree
(Thread 1 and most of 4 fall to the name check that already exists, widened
to command names and to the human surfaces); and a supersession record is
kept only while it cites the pin `tests/pins.json` currently holds (the
first pass's Thread A). Everything else in this report is a member of that
one change-set or an ordinary deletion.

## Convergence with `REVIEW-2026-09-03.md`

Both passes, independently, reached: the supersession ratchet and its
29%; `stages`/`assembly` and the two dead adapter fields; the dead
functions; the live harnesses; browser-game's carve-out;
`super-research`'s unresolvable skill; the PyPI-dependent installer test;
the stale README counts. Distinct to this pass: the ghost `cutcheck`
across four owners, `review-invalid` and `successors.md`, the phantom
lifecycle rows, the sealed `independence` field, the eight dead flags, the
160/185 facade census, the canary and UI fixtures frozen on retired
executors, the routing-benchmark apparatus as a closed experiment, the
three-vs-four rings, the Details rule's three owners, the `"gate's row"`
anchor, the html-dossier Lens gap, DESIGN's self-contradiction at `:470`
and `:479`, the broken `scripts/ui.py` command, the platform route table,
and the test apparatus as its own thread. Where the two disagree on remedy:
the first pass renames `four`; this pass deletes the flag with the
experiment that needed it.
