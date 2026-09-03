# Workflow ladder: build spec (2026-09-02, revision 2)

Status: proposed, sliced into tickets under `research/workflow-ladder-tickets/`
(driver: `RUN.md` there). Base: `main` at `6b02c226` (PR #170, per-item
environments) or later. Design source: "One Interpreter, Two Verbs"
(https://claude.ai/code/artifact/41d1015e-19d0-4287-a88b-c868b0a35ad3). Plain-English
companion: `research/workflow-ladder-conversion-guide-2026-09-02.md`.

This file is carried in the run's root Context. Every unit is one `tickets.py do`
with a Goal that is one observable end result and a `done` that is a command.
Names in §2 are fixed so units running in parallel agree without talking.

## 0. Decisions adopted

Closed. A planner does not reopen them; a child that finds one wrong reports the
observation and continues.

1. **Composition stays prose in one interpreter.** A workflow is prose the root
   runs; a reusable workflow is invoked by name as a frame under the caller's
   (`frame-open --parent`). No child drives a frame for primary work
   (delegation §4 stands). Every host stays at subagent depth 1.
2. **Four kinds of part, four boundaries.** Script (function), callable
   (context: `do`/`judge`, optionally an applied skill as its body and sheets as
   extra craft), workflow (frame), knowledge (none: prompt, sheet, pack). The
   perfect-model test in DESIGN.md decides admission.
3. **Sheets are a stamped ring item kind**, digest-pinned on the ticket like a
   pack, read by maker and judge at the same digest.
4. **`--skill` is a pinned field**, not a path written into a goal file.
5. **Control-flow sentences are idioms**, owned once in
   `docs/custom-workflow-authoring.md` §Idioms and quoted verbatim.
6. **The trunk prints the frame law at `frame-open`**; bodies stop carrying it.
7. **Reusable, domain-blind workflows ship in `skills/workflows/`** (T1, the tier
   ARCHITECTURE.md already defines as "domain-blind behavior", empty today).
   Domain-bearing workflows stay in `example-workflows/` (T3). The lib resolves
   workflows across both directories; a name present in both is a validator error.
8. **Three dependency classes, three homes.** An item's own Python tooling:
   `requirements.txt` beside the manifest, one private environment per item
   (PR #170, unchanged). An item's non-Python tooling: declared in `tools.txt`
   beside the manifest and checked, never installed; Node packages for an
   item's own scripts: `package.json` plus lockfile beside the manifest,
   installed by `orchflows sync` into the item's `node_modules/`. The
   artifact's dependencies (the game's three.js): the workspace's own manifest,
   installed by the child in its worktree, lockfile committed with the artifact;
   orchflows never owns them. Sheets carry no scripts and no dependencies.
9. **A bundle has a manifest.** `.orchflows/BUNDLE.md` with `name`, `version`,
    `requires` (pinned bundle references). `orchflows add` follows `requires`
    into `imports.lock`.
10. **`orchflows check`** runs the library's validator over a ring.
11. **Not in this run:** a workflow that builds workflows (deferred by the user), delegated drivers, result reuse by seal, pack
    inheritance, a `uv`-based environment builder, bundle-qualified names,
    any change to the five packs' crafts beyond one sentence, growth of the
    host block (400 words) or `AGENTS.md` (230 words).

## 1. Non-goals

- No third kernel verb. `orch-do` and `orch-judge` gain sentences, not sections.
- No template, instantiate, or shape-expansion machinery.
- No renaming of packs, no change to `hosts/` depth caps, no rename of
  `example-workflows/`.
- No conversion of items not on `main` (tiktok-video on PR #166, paper-repro on
  `claude/hackernews-workflow-brainstorm-5f52ba`): successors, §6.

## 2. Names and shapes fixed by this spec

| term | fixed as |
|---|---|
| ring item kind `sheet` | ring dir `sheets/`; lib dir `sheets/`; manifest `SHEET.md`; `orch-` reserved like the other kinds; no host adapter (stamped, never invoked); a `by-name/<name>/SHEET.md` pointer like packs; no `scripts/`, no `requirements.txt`, no `tools.txt` (validator refuses) |
| sheet frontmatter | `name` (= folder), `description` (≤140 chars), `packs:` (pack names it may be stamped beside; any other pack refuses) |
| sheet sections | `## Craft` (required), `## Lens` (required; `###` entries keyed by artifact kind as `contracts/pack-signature.md` keys a craft's Lens: `git`, `doc`, `evidence`), `## Vocabulary` (optional). `## Workspace`, `## Stages`, `## Spec fields` refused: pack-only |
| sheet rule | additive and tighten-only. Where a sheet loosens the craft, the craft wins and the judge reports the conflict as a finding tagged `sheet-defect` |
| sheet budget | `SHEET_BUDGET = 100` non-empty lines, enforced beside `CRAFT_BUDGET` |
| sheet digest | sha256 over the sheet directory tree (sorted relative paths + bytes) |
| skill digest | sha256 over the skill directory tree excluding `tests/`, `__pycache__/`, `node_modules/` |
| ticket fields (T0) | `sheets: [name, ...]`, `sheet_digests: {name: sha256}`, `skill: name`, `skill_digest: sha256`; all optional; one T0 supersession record in `contracts/work-item.md` |
| pinned-item plumbing | one function family in a new `scripts/tickets_pins.py`: resolve a `(kind, name)` nearest-first through `rings.item_roots`, digest it, pin at issue, re-verify at every later door, one refusal text naming the item, the ring it resolved in, and the digest pair. `pack_digest` is not migrated; the new kinds use the new module |
| `--sheet` | repeatable on `tickets.py do` and `judge` |
| `--skill` | on `tickets.py do` and `judge`; refuses an `orch-` name; refuses when the skill's `role` is not the verb's (`do` → `worker`, `judge` → `planner`); `executor` stays `orch-do`/`orch-judge` |
| launch prompt, sheet line (do) | after the craft lines, one per sheet: ``Read the sheet `<name>` at <path> whole (sha256 <digest>). Its `## Craft` binds your making; its `## Lens` `### <kind>` entry adds to the craft's `### <kind>` and never loosens it.`` |
| launch prompt, sheet line (judge) | ``Read the sheet `<name>` at <path> whole (sha256 <digest>). Its `## Lens` `### <kind>` entry adds criteria you check beside the craft's; where it loosens the craft's, the craft wins and you report the conflict as a `sheet-defect` finding.`` |
| launch prompt, applied skill | `_identity_line` names the applied skill: ``Call the Skill tool with skill `<name>` and pass this entire prompt, verbatim, as its arguments. Already running as that skill, do the work here and never invoke it again.`` then ``Your kernel contract is `orch-do` at <by-name path>: read it; its Require, Never and Return bind this ticket; the applied skill is the method.`` (`orch-judge` for a judge). When the applied skill declares an environment, one more line: ``Its scripts run through the interpreter `orchflows env skill <name>` prints.`` |
| frame-open payload | gains `workflow_path` (resolved `SKILL.md` when `--workflow` is given; refusal naming the rings searched when it does not resolve) and `law` (three fixed lines, U3) |
| lib workflow dirs | `rings.LIB_DIRS["workflow"]` becomes the ordered list `["skills/workflows", "example-workflows"]`; `tools/validate.py` refuses a name present in both |
| `tools.txt` | beside an item's manifest; one tool per line: `<name> [<pep440-style version spec>] [:: <probe command>]`, or `env <NAME>` for a required environment variable. `orchflows sync` and `orchflows check` report each missing tool or variable with its line; nothing is installed and no variable's value is printed |
| Node tooling for an item's scripts | `package.json` and a lockfile (`package-lock.json` or `pnpm-lock.yaml`) beside the manifest; `orchflows sync` runs the lockfile install (`npm ci` or `pnpm install --frozen-lockfile`) in the item directory when the item is trusted and `node` resolves; untrusted or node-less: skipped with the remedy, like `requirements.txt`. `node_modules/` is written to the ring `.gitignore` block and to the project's by `sync --project` |
| environment pruning | `orchflows sync` removes `~/.orchflows/envs/<kind>/<name>/` for items no longer in the inventory, and says so |
| `.orchflows/BUNDLE.md` | frontmatter `name` (the bundle's name; the home ring's is the user's choice), `version` (a tag or a date), `requires:` (list of `<git-url>@<pin>`); body free prose. `orchflows add` reads it after clone and adds each `requires` entry to `imports.lock` transitively; a cycle or an unpinned entry refuses. A bundle without one is a bundle with no requirements |
| `orchflows check [<ring-dir>]` | runs the validator's item checks (anatomy, budgets, call-edge resolution, sheet Lens keys against named packs, `packs:` resolution, `tools.txt` grammar, `BUNDLE.md` shape) over the project ring when standing in a project, else the home ring, or the directory given; exit 1 on any refusal |
| rungs (vocabulary) | `applied skill`, `sheet`, `reusable workflow`, `glue workflow`, `idiom`; `brick` stays retired |
| recurrence rule (law) | a step that holds at least one callable and recurs across two or more workflows, or whose run deserves its own journal, is a reusable workflow invoked by name; a step with no callable of its own is a sentence; a recurring sentence's wording is an idiom |
| placement rule (law) | an item lives in the innermost ring that contains every caller: one project, the project ring; two, the home ring; other people, a bundle they import |
| idioms | `bounded-repair`, `fan-out`, `freeze`, `declare-gaps`, `outside-close` (wording in U4) |
| gallery items added | `skills/workflows/`: `checkpointed-build`, `bakeoff`; `sheets/`: `market-brief`, `html-dossier`, `sheet-craft` |
| the repo's own bundle | `.orchflows/` holds only bundle content (`skills/`, later `sheets/`, `BUNDLE.md`); design notes, reviews and run scratch move to `research/` or `.orch-notes/` |

## 3. Units

Every unit: pack `orch-code-pack`, `--isolation required`, evidence `git:`; judged
by a code-pack judge over the `git:` line with `bounded-repair`. `done` commands
run through the verified interpreter (`uv run --no-project python` here). Every
`done` includes `python tools/validate.py`, and every budget is part of it.

### U0 · Contracts, ring kind, pin plumbing, flags

**Goal.** `contracts/work-item.md` carries the four optional fields with one T0
supersession record; `contracts/sheet.md` owns the sheet shape (§2) with its
generated T0 block; `contracts/pack-signature.md` points at it in one sentence;
`scripts/rings.py` knows kind `sheet` (`KINDS`, `RING_DIRS`, `LIB_DIRS`,
`MANIFESTS`); `scripts/tickets_pins.py` resolves, digests, pins and re-verifies a
`(kind, name)` as §2 fixes; `tickets.py do|judge` accept `--sheet` (repeatable)
and `--skill`, pin them into the frontmatter through that module, and refuse on
drift at every later door. No prompt line, no role check, no `packs:` check yet:
those are U1 and U2.

**Details.** Files: `contracts/work-item.md`, `contracts/sheet.md` (new),
`contracts/pack-signature.md`, `scripts/rings.py`, `scripts/tickets_pins.py`
(new), `scripts/tickets_mint.py` (flags), `scripts/tickets_issue.py` (pinning),
the doors that verify `pack_digest` (mirror them for the new fields), tests.
Regenerate whatever `tools/validate.py` hash-pins. The supersession sentence:
"`sheets`/`sheet_digests` pin stamped sheets and `skill`/`skill_digest` pin an
applied skill at issue; every later door verifies the resolved item against its
digest." `dispatch.md` is untouched. Tests: nearest-first resolution across
project/home/lib for both kinds; drift refusal; a `do` without the flags emits
today's frontmatter and prompt byte for byte.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope contracts,scripts,tests,tools && python tools/run_serial_compat.py --write-manifest`

### U1 · Sheets: semantics, prompt, scaffold, validator, install

**Goal.** A `--sheet` whose `packs:` excludes the stamped pack refuses; the
launch prompt carries one sheet line per sheet in the §2 wording for `do` and
for `judge`; `orchflows new sheet <name>` scaffolds a validating sheet;
`orchflows list --kind sheet` lists; `orchflows sync` writes no adapter for
sheets; `install.py` copies lib `sheets/` and mints `by-name/<name>/SHEET.md`;
`tools/validate.py` enforces sheet anatomy, `SHEET_BUDGET`, `packs:` resolution,
Lens keys against the named packs' adapter kinds, and refuses `scripts/`,
`requirements.txt`, `tools.txt` or a pack-only section inside a sheet.

**Details.** Files: `scripts/tickets_dispatch_launch_lines.py` (add
`_sheet_lines` after `_craft_lines`), `scripts/tickets_mint.py` (`packs:`
refusal), `scripts/orchflows.py`, `scripts/orchflows_scaffold.py`,
`scripts/orchflows_adapters.py`, `installer/` (lib copy, by-name),
`tools/validate_support/common.py` (`SHEET_BUDGET`), `tools/validate_support/packages.py`.
Tests: prompt lines present and verbatim for both verbs; `packs:` refusal;
scaffold validates; validator refuses a sheet with `## Workspace` and one with
`scripts/`.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope scripts,tests,tools,installer && python tools/run_serial_compat.py --write-manifest && python install.py --dry-run`

### U2 · Applied skills: role check, identity line, environment line

**Goal.** `--skill` refuses an `orch-` name and a role mismatch; the launch
prompt's identity line enters the applied skill with the kernel-contract line,
and adds the environment line when the skill declares `requirements.txt`;
`executor` and role resolution are unchanged.

**Details.** Files: `scripts/tickets_dispatch_launch_lines.py` (`_identity_line`),
`scripts/tickets_mint.py` (refusals), `scripts/orchflows_envs.py`
(`requirements_of` for the environment line). The kernel-contract path is the
`by-name/orch-do/SKILL.md` (or `orch-judge`) path the installer mints. Tests:
role mismatch (`--skill` naming a `role: planner` skill on `do`); `orch-`
refusal; identity line verbatim with and without a declared environment.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope scripts,tests && python tools/run_serial_compat.py --write-manifest`

### U3 · The trunk prints the frame law; two lib workflow dirs; bodies drop the paragraph

**Goal.** `frame-open` returns `workflow_path` and a `law` list of exactly
three lines: (1) "Before each call, re-read this frame's `## Report` and its
children's states." (2) "After each call, append the decision with `tickets.py
result <run> <frame> --by <frame>`; keep every returned `artifact:` and
`findings:` line verbatim and hand the line itself to the next goal file." (3)
"Close with `tickets.py frame-close <run> <frame> --done <command>` run outside
the children; a close over two or more `do` children needs a judging child or an
`unjudged: <reason>` line." `rings.LIB_DIRS["workflow"]` resolves across
`skills/workflows` then `example-workflows`, and the validator refuses a name in
both. The eight gallery bodies carry no ledger/relay paragraph and each still
validates under 450 words with no domain sentence and no `Never` changed.

**Details.** Files: `scripts/tickets_frame.py` (`frame_open` payload; the law
lines are one tested constant), `scripts/rings.py` (`LIB_DIRS`, `item_roots`),
`tools/validate.py` (dual-dir refusal), the eight bodies under
`example-workflows/` (benchmaker, browser-game, drift-canary, evolve, renovate,
self-improve, skill-tournament, super-research). Keep each body's `Return:
tickets.py frame-close …` line: it is the contract. The `installer` already
copies `skills/` wholesale; confirm `skills/workflows/*` gets adapters like
`example-workflows/*` and add the test if none exists.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope scripts,tests,example-workflows,installer && git diff --check`

### U4 · Law and docs

**Goal.** The library's prose names the ladder once, in each fact's owner, inside
every budget: `docs/vocabulary.md` defines the five rungs; `rules/composition.md`
gains the recurrence rule and the sentence that a sheet or applied skill is
stamped by the caller and read only by that ticket's maker and judge;
`docs/custom-workflow-authoring.md` replaces "start from the nearest body" with
the four-questions-then-rung recipe, gains §Idioms (the five sentences in
Details), the placement rule, §7's ring table with `sheets/`, a §Dependencies
rewrite naming the three classes and the three files (`requirements.txt`,
`tools.txt`, `package.json`) and the artifact rule, and drops "write both into
the prose" for "the trunk prints the frame law"; `rules/token-economy.md` §11
places sheets in the every-dispatch tier at `SHEET_BUDGET`; `ARCHITECTURE.md`
places sheets under T2 in one sentence and states that T1 `skills/workflows/`
holds the reusable domain-blind workflows; `rules/delegation.md` §2 lists the
sheet, applied-skill and environment lines among what the launch prompt
carries; `docs/pack-authoring.md` gains the pack-versus-sheet admission
sentence; `DESIGN.md` gains one "Why sheets and applied skills" paragraph
applying the perfect-model test and one "Why three dependency classes"
paragraph.

**Details.** One fact, one owner: the recurrence and placement rules live in
`rules/composition.md` and are linked, never restated. Idioms, each under 30
words: `bounded-repair`: "Where the judge blocks, one repair `do` is handed the
`findings:` line verbatim, then one re-judge; two rounds is the bound."
`fan-out`: "One `do` per named item, launched together under the frame; the
shape line lists them as one wave." `freeze`: "Fix the identity before any
candidate exists and forbid every later call from touching it."
`declare-gaps`: "A gap that remains is written as a gap, `[]` when there is
none; silence is a defect." `outside-close`: "Close on a command run outside
every child; never on a child's own claim." Host block and `AGENTS.md` unchanged.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope docs,rules,tests,tools`

### U5 · Kernel sentences

**Goal.** `skills/kernel/orch-do/SKILL.md` and `orch-judge/SKILL.md` each carry
one sentence on sheets (the maker reads every handed sheet whole and its Lens
entries add to the craft's; the judge checks the craft's entry and every sheet's
and reports a loosening as `sheet-defect`) and one clause on applied skills (the
applied skill is the method; Require, Never and Return still bind), each under
300 words, both still primitives.

**Details.** No new section, no domain, no pack name, `role` lines unchanged.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope skills,tests`

### U7a · Sheets `market-brief`, `html-dossier`, `sheet-craft`

**Goal.** Three lib sheets validate at `SHEET_BUDGET` and install to `by-name/`:
`sheets/market-brief` (`packs: [orch-research-pack]`; Craft: audience, pains,
three or more competitors with their hooks, live trends, every claim cited and
dated, the window named; Lens `### evidence`: source and date per claim, gaps
declared); `sheets/html-dossier` (`packs: [orch-content-pack, orch-design-pack]`;
Craft: one self-contained HTML file, no external fetch, legible light and dark,
tabular numerals, a sources section; Lens `### doc`: opens offline, every figure
captioned, every claim links its source inside the file); `sheets/sheet-craft`
(`packs: [orch-content-pack]`; Craft: what a sheet is, knowledge only, cited,
tighten-only Lens, `SHEET_BUDGET`; Lens `### doc`: every Craft claim traceable
to a source in `references/` or the ticket's Context, every Lens entry names
what proves it, no step, no command, no dependency).

**Details.** Files under `sheets/`. Knowledge only. The super-research report
rules are absorbed by `html-dossier`.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope sheets,tests && python install.py --dry-run`

### U7b · `checkpointed-build`

**Goal.** `skills/workflows/checkpointed-build/SKILL.md` (≤450 words) with
`Require: goal, pack, judge-pack, sheets ([] when none), probe, bound, workspace`,
run as: plan (`do --makes cut`, the waves' pack) → one `do` per wave at the
cut's level, `--isolation required`, every sheet stamped (`fan-out`) → judge
(`judge-pack`, same sheets, over the joined `git:` line) → `bounded-repair` →
`Return: artifact: git:<tip>` and `findings:` relayed verbatim, closing on
`probe` (`outside-close`); the plan step's cut pins the artifact's dependency
set in its first wave and later waves add none without reporting a deviation.

**Details.** Domain-blind. Nearest bodies: the render→judge→repair tail of
`C:\Users\danhm\.orchflows\workflows\tiktok-video\SKILL.md` and the vampire-fps
build run `20260902T150541Z-vampire-fps-build`. `rules/topology.md` §5, §8.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope skills,tests`, plus one scratch run on a fixture (a two-file repository with a failing test and a probe that runs it) whose frame closes `complete`.

### U7c · `bakeoff`

**Goal.** `skills/workflows/bakeoff/SKILL.md` (≤450 words) with `Require:
candidates (named list, one-line brief each), pack, rubric (a sheet name), bound`:
one isolated `do` per candidate launched together under opaque ids → one `judge`
over every candidate's line with the rubric sheet stamped → `Return: winner:
<artifact line>` and `findings:`; `Never`: reveal the incumbent to the judge; run
candidates serially.

**Details.** Nearest body: `example-workflows/evolve/SKILL.md` (blind scoring).
One judge, one artifact kind.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope skills,tests`, plus one scratch run with two trivial candidates whose frame closes `complete`.

### U7d · Convert `super-research`

**Goal.** `example-workflows/super-research/SKILL.md` reaches its skill by
`--skill research-acquire`, stamps `html-dossier` on the report `do`, carries no
mechanics paragraph, and is shorter with every domain sentence and `Never` kept;
the skill's ring item is renamed from `.orchflows/skills/super-research/` to
`.orchflows/skills/research-acquire/` (Python package and tests keep their
names), its `requirements.txt` untouched, and `orchflows sync --project`
regenerates the project adapters so no two items share a name.

**Details.** The acquisition `do`s become `do --pack orch-research-pack --skill
research-acquire --goal-file <f> --parent <frame>` with the per-source goal files
unchanged. Depends on U11 having cleared `.orchflows/` of non-bundle files first.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope example-workflows,.orchflows,tests && python install.py --dry-run`, plus one scratch run of the converted workflow on a one-source question whose frame closes `complete`.

### U8 · Dogfood: `browser-fps`

**Goal.** In the home ring: sheets `threejs` (`packs: [orch-code-pack,
orch-design-pack]`; craft and checks for a browser FPS on three.js from the
vampire-fps run's evidence and current docs; its Craft names the toolchain:
pnpm, node 20 or newer in `engines`, vite, the lockfile committed,
`node_modules/` ignored) and `fps-design` (`packs: [orch-content-pack,
orch-design-pack]`; level, input, feel, what blocks), each authored by a content
`do` stamped `sheet-craft` and validating under `orchflows check`; a glue
workflow `browser-fps` (≤200 words) with a `tools.txt` naming `node >= 20`,
`pnpm`, and the probe's needs, that runs one research `do` (research pack,
bounded) for the engine that fits this brief, with evidence, in parallel with a
brief `do` stamped `fps-design`, then `checkpointed-build` with the code pack,
`threejs` on the waves, the design pack and `fps-design` on the judge, closing
on a playable probe (the site loads, a level starts, input moves the player);
and one run of `browser-fps` on the fixture "a one-room vampire-themed browser
FPS, keyboard and mouse, shipped as a static site" that closes `complete` on
that probe within the bound. The glue names no item outside the library
(`checkpointed-build`, the packs, its own sheets), so the run proves sheets,
`--sheet`, `tools.txt` and `checkpointed-build` on nothing a fresh install lacks.

**Details.** Reference workspace `C:\Users\danhm\tools\vampire-fps`; runs
`20260902T063434Z` (engine bake-off) and `20260902T150541Z-vampire-fps-build`.
Author the sheets and the glue under this unit's frame as `do` children (content
pack for the sheets and the body, code pack for the probe script), judge them
against `rules/composition.md` and `docs/custom-workflow-authoring.md` with
`bounded-repair`, then install with `orchflows sync` and run. `--bound` on the
build waves; if spent, the frame closes `limited` with the successor written
and the unit reports that honestly. Artifact dependencies live in the
worktree's `package.json`, never in a ring item. Where `super-research` is
installed the glue may name it for the engine step; this run does not, so the
result does not depend on it.

**Done.** `python tools/validate.py`, the `browser-fps` frame's `frame-close --done <probe>` exit code, `orchflows list --kind workflow` naming `browser-fps`, and `orchflows check` green on the home ring.

### U9 · Bundle manifest

**Goal.** `orchflows add <url>@<pin>` reads the cloned bundle's
`.orchflows/BUNDLE.md`, adds each `requires` entry to `imports.lock`
transitively, refuses a cycle or an unpinned entry naming the offending
manifest, and restores the closure on `orchflows sync`; `orchflows new bundle`
scaffolds a `BUNDLE.md` in the ring at hand; the repo's own `.orchflows/BUNDLE.md`
exists with `name: orchflows-contrib`, this revision's date as `version`, and
`requires: []`; `contracts/bundle.md` owns the shape.

**Details.** Files: `scripts/orchflows_home.py` (add, restore, lock),
`scripts/orchflows_scaffold.py`, `scripts/orchflows.py`, `contracts/bundle.md`
(new), `.orchflows/BUNDLE.md` (new), `docs/custom-workflow-authoring.md`
§Publish (one sentence; U4 owns the rest of that doc, so this unit edits only
that section). Tests: transitive closure of two fixture bundles; cycle refusal;
unpinned refusal; a bundle without a manifest imports as before.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope scripts,tests,contracts && python tools/run_serial_compat.py --write-manifest`

### U10 · `orchflows check`

**Goal.** `orchflows check [<ring-dir>]` runs the validator's item checks over
the project ring when standing in a project, else the home ring, or the
directory given, and exits 1 on any refusal; its checks are the same functions
`tools/validate.py` runs over the library, so a refusal reads the same in both.

**Details.** Files: `scripts/orchflows.py` (subcommand), a thin
`scripts/orchflows_check.py` that imports the check functions from
`tools/validate_support/` (they must run from the installed `bin/` layout too:
verify the import path or copy the needed modules at install), `installer/`
if the validator support has to ship. Tests: a valid home-ring fixture passes; a
sheet with `## Workspace` fails; a workflow body over budget fails; a dangling
call edge fails.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope scripts,tests,tools,installer && python install.py --dry-run`

### U11 · The repo's own bundle is only a bundle

**Goal.** `.orchflows/` in this repository contains only `skills/` (and later
`sheets/`, `BUNDLE.md`); `lego-design-2026-08-31.md`,
`routing-design-2026-08-31.md`, `self-improve-design-2026-09-01.md` move to
`research/`; `reviews/`, `lego-migration/`, `self-improve-delivery/`,
`super-research/` move under `research/run-notes/` with their history intact
(`git mv`); every path that referenced them (grep the tree, including memory
pointers cited in `research/`) is updated; nothing under `.orchflows/skills/`
changes.

**Details.** `git mv` only, plus reference fixes. The one memory file that
links the lego design by path is outside the repo; note the new path in the
`## Report` so the user can update it.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope .orchflows,tests && git diff --check`

### U12 · Tools, Node tooling, environment pruning

**Goal.** `orchflows sync` reads each item's `tools.txt` (grammar in §2) and
reports every missing tool or variable with its line and installs nothing;
runs the lockfile install for an item's `package.json` into the item's
`node_modules/` when the item is trusted and `node` resolves, else reports the
remedy; removes `~/.orchflows/envs/<kind>/<name>/` for items no longer in the
inventory; the ring `.gitignore` block and the block `sync --project` writes
both carry `node_modules/`; `orchflows check` validates `tools.txt` grammar;
`orchflows env <kind> <name>` is unchanged.

**Details.** Files: `scripts/orchflows_envs.py` (tools, node, prune),
`scripts/orchflows_home.py` (`.gitignore` block), `scripts/orchflows_adapters.py`
(`sync --project` ignore lines), `scripts/orchflows.py` (report lines). A probe
command in `tools.txt` runs with a short timeout and its exit code decides; a
line without a probe resolves the name on `PATH`. Version specs compare against
`<tool> --version` output only when a probe is absent and the output's first
version-shaped token parses. Tests: missing tool reported, present tool silent,
`env NAME` reported without printing a value, node install skipped when
untrusted, prune removes exactly the orphan.

**Done.** `python tools/validate.py && python tools/run_tests.py --scope scripts,tests && python tools/run_serial_compat.py --write-manifest`

## 4. Order

    U0 > [U1, U2, U3, U4, U11] > [U5, U7a, U7b, U7c, U9, U10, U12] > U7d > U8 > gate

U1 and U2 share U0's fields and resolver. U3, U4, U11 need nothing but the
base. U7a waits on U1; U7b and U7c on U3 and U4; U9, U10 and U12 on U4 only
for their doc sentences. U7d waits on U2, U7a, U11. U8 waits on U7a, U7b, U12.

## 5. Gate

At the joined tip, once, outside every child:

    python tools/run_required.py --no-cache
    python tools/run_serial_compat.py --write-manifest   # rerun the five if the manifest changed
    python install.py --dry-run
    git diff --check

Then: the host block's word count is no higher than on `main` and `AGENTS.md`
is byte-identical; every budget green; `install.py`; `orchflows sync` at home
(this also mints the missing `tiktok-video` adapter); `orchflows check` green on
the home ring; `orchflows list` shows the two new workflows and three sheets. A seam judge
over the joined tip, a content judge over every gallery body touched, against
`rules/composition.md` and `docs/custom-workflow-authoring.md` as amended.

## 6. Successors (not this run)

- Convert `tiktok-video` after PR #166 merges: `market-brief` on the brief, the
  two reference files become sheets `tiktok-script` and `tiktok-render`, the
  render pipeline's Python declares `requirements.txt` and `tools.txt` (ffmpeg),
  render→judge→repair becomes `checkpointed-build`.
- Convert `paper-repro` after its branch lands: intake sheet, two
  `checkpointed-build` instances.
- A `uv`-based environment builder (`uv venv` + `uv pip sync`, or PEP 723 inline
  metadata for single-file scripts) behind the same `orchflows env` door, for
  Python-version pins `requirements.txt` cannot express.
- Bundle-qualified names (`<bundle>/<name>`) when two imported bundles collide.
- Delegated driver (Claude only), if root-serial driving is measured as the
  bottleneck. Result reuse by assignment seal as a windowed policy.
- A `program-record` sheet for browser-game, and a name that says what it is.
- A workflow that builds workflows from one sentence, on the two callables
  only (outline `do --makes root`, slice `do --makes cut`, work `do`, review
  `judge`), and the host-block line that would route authoring requests to it.
  Deferred by the user on 2026-09-02.

## 7. File layout

The mapping that decides where a file goes:

| Python | orchflows |
|---|---|
| the interpreter and stdlib you install once | `~/.orchflows/lib`, `bin`, `runtime` (`install.py`) |
| the package you maintain and push | the home ring `~/.orchflows/{skills,packs,sheets,workflows}`, a git repo |
| a project's own package | the project ring `<project>/.orchflows/`, committed |
| `pip install git+…@tag` and its lockfile | `orchflows add <url>@<pin>`, `imports/`, `imports.lock` |
| `pyproject.toml` `dependencies` | `.orchflows/BUNDLE.md` `requires` |
| `sys.path` order | nearest first: project, home, imports, lib |
| names you must not shadow | the `orch-` floor |
| a tool's own venv | `~/.orchflows/envs/<kind>/<name>/` and the item's `node_modules/` |
| `~/.local/state` | the state sink (`rules/visibility.md` §6): runs, tickets, friction |
| console-script entry points | host adapters, written by `orchflows sync` |
| running your library's tests | `orchflows check` |

The library repository:

    orchflows-public/
    ├── contracts/            T0  data shapes                        + sheet.md, bundle.md
    ├── rules/  docs/             law and vocabulary
    ├── skills/
    │   ├── kernel/           T1  orch-do, orch-judge
    │   └── workflows/        T1  checkpointed-build, bakeoff                     (domain-blind, reusable)
    ├── packs/                T2  the five packs
    ├── sheets/               T2  market-brief, html-dossier, sheet-craft         (domain data)
    ├── example-workflows/    T3  browser-game, super-research, benchmaker, …      (domain-bearing)
    ├── scripts/ tools/ tests/ installer/ hosts/ templates/
    ├── research/                 specs, reviews, run notes (never installed)
    └── .orchflows/               this repo's own bundle: BUNDLE.md, skills/research-acquire/ (has requirements.txt)

The user's machine:

    ~/.orchflows/                       the user's library: a git repo they push
    ├── BUNDLE.md                       name, version, requires
    ├── skills/<name>/                  SKILL.md, scripts/, references/, tests/, requirements.txt, tools.txt, package.json
    ├── packs/<name>/                   SKILL.md, references/craft.md
    ├── sheets/<name>/                  SHEET.md, references/            (no scripts, no dependencies)
    ├── workflows/<name>/               SKILL.md, references/, tools.txt
    ├── imports/  imports.lock          pinned bundles                    (imports/ ignored)
    ├── envs/  lib/  bin/  runtime/     machine-local, regenerable        (ignored)
    ├── state/                          runs, tickets, friction           (ignored)
    └── .gitignore                      written by `orchflows sync`; also ignores node_modules/

    <project>/
    ├── .orchflows/                     the project's own bundle, committed: BUNDLE.md, sheets/, workflows/, skills/
    ├── .claude/skills/                 adapters from `orchflows sync --project`, committed
    ├── .orch-notes/                    scratch and goal files, ignored
    ├── scripts/probe.py                app code a `done` command runs
    └── src/ package.json …             the artifact and its own dependencies

The placement rule and the recurrence rule are law (§2). Everything under
`example-workflows/` and `skills/workflows/` is installed; `research/` never is.

## 8. Dependencies and environments

Three classes. Each has one home and one file, and the classes never share an
environment.

| class | example | file | who builds it | where it lives |
|---|---|---|---|---|
| an item's own Python tooling | `research-acquire`'s adapters, a render pipeline | `requirements.txt` beside the manifest | `orchflows sync` (PR #170) | `~/.orchflows/envs/<kind>/<name>/` |
| an item's non-Python tooling | ffmpeg, node, pnpm, a browser for captures, an API key | `tools.txt` beside the manifest | nobody: declared and checked | the machine; `orchflows sync`/`check` report what is missing |
| an item's Node tooling | a capture script on playwright | `package.json` + lockfile beside the manifest | `orchflows sync` (U12) | the item's `node_modules/`, ignored |
| the artifact's dependencies | three.js, vite, the game's assets | the workspace's own manifest (`package.json`, `pyproject.toml`) | the child, in its worktree, as part of making the artifact | the worktree; lockfile committed with the artifact |

Rules:

- An item's scripts run through the interpreter `orchflows env <kind> <name>`
  prints. Prose names that command, never a path.
- An item's scripts import nothing from another item. Shared behaviour is a
  skill you call, not a module you import.
- A sheet carries knowledge only. When knowledge is "use pnpm and node 20", that
  sentence lives in the sheet's Craft and the requirement lives in the glue
  workflow's `tools.txt`, where `sync` can check it.
- Lib items (kernel, packs, sheets, `skills/workflows/`, `example-workflows/`)
  declare no dependencies: the library's stdlib floor. First-party items with
  dependencies live in the repo's own `.orchflows/` bundle and reach users
  through `orchflows add`.
- The artifact's toolchain is decided in the plan step's first wave and pinned
  by its lockfile; a later wave that must add a dependency reports the
  deviation. The `done` probe runs in the integrated tree with the same
  toolchain, which the glue workflow declares in `tools.txt`.
- Parallel wave worktrees share the package manager's content-addressed store
  (pnpm's, pip's wheel cache), so N worktrees cost one download.

Edge cases and what happens:

| case | behaviour |
|---|---|
| no network at `sync` | the environment build fails; `sync` names the item and the remedy; a launch of that item refuses with the unbuilt remedy (exists) |
| no network in a child installing artifact deps | the child reports it in `## Report`; the probe fails honestly; nothing is faked |
| untrusted project item with dependencies | skipped with `orchflows trust <bundle>` as the remedy (exists); same for `package.json` |
| two items pin conflicting versions | no conflict: one environment per item |
| an item needs a Python newer than the runtime's | `requirements.txt` cannot say so; declare `python >= 3.11 :: python --version` in `tools.txt` so `check` reports it; the `uv` builder is the successor |
| platform-specific wheels | pip environment markers in `requirements.txt`; `tools.txt` lines may carry a probe that fails on the wrong platform |
| a 2 GB model dependency | allowed; the first `sync` is slow; the sheet says to prefer a system tool with a probe over a heavy wheel where one exists |
| an API key | `env NAME` in `tools.txt`; reported missing by name, never printed; the script reads the variable |
| N parallel waves each installing `node_modules` | pnpm store dedupes; the sheet prescribes pnpm; the first wave commits the lockfile |
| two waves both change the lockfile | `land` reports the overlap like any conflict; the deviation rule makes it rare |
| the probe needs a tool the children had | the glue workflow's `tools.txt` declares it; `sync` checked it before the run |
| an item ships Python and Node scripts | both files beside the manifest; both built by `sync`; `orchflows env` prints the Python interpreter, `node` resolves on `PATH` |
| an item is removed from the ring | `sync` prunes its environment and says so |
| Codex or Grok host | the same files and commands; nothing here is Claude-specific |
| a sheet with a script in it | the validator refuses; the script belongs to a skill the sheet may name |
