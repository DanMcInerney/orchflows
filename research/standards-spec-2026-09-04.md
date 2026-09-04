# Standards: one kind for domain craft and its narrowings

Status: proposed, sliced into tickets under `research/standards-tickets/`
(driver: `RUN.md` there). Base: `main` at `6d47143e` or later.

Retires three nouns — `pack`, `sheet`, `craft` — and replaces them with one:
a **standard**. A standard states what a good artifact carries in some
domain. A standard may `narrows:` exactly one other standard, which is how
specificity cascades: `three-js` narrows `javascript` narrows `code`. The
worker reads the resolved chain broad to narrow; the judge reads the
identical chain at the identical digests.

This file is carried in the run's root Context. Every unit is one
`tickets.py do` whose Goal is one observable end result and whose `done` is
a command. Names in §2 are fixed so units running in parallel agree without
talking.

## 0. Decisions (closed)

A planner does not reopen these. A child that finds one wrong reports the
observation in `## Report` and continues.

1. **One noun.** `pack`, `sheet` and `craft` all retire. Everything is a
   `standard`. A standard with no `narrows:` is a **root**; one with
   `narrows:` is a narrowing. Rejected: keeping a second noun for
   narrowings (`specialty`, `subpack`). The two behave identically — same
   format, same digest rule, same tighten-only rule, same reading — so a
   second noun is a second owner of one concept. It would also become a lie
   the day routing reaches a narrowing, which decision 6 leaves open.
2. **`narrows:` names exactly one parent.** Chains give depth; a tree gives
   reuse. Rejected: many parents. All three shipped sheets name exactly one
   pack today, so nothing in the library loses expressiveness.
3. **Exactly one adapter across a ticket's resolved standards.** Declared by
   whichever standard introduces the domain, not necessarily the root — so a
   domain-blind standard (a house style) can sit above `code` and `design`
   without duplicating itself or claiming a workspace mechanism it has no
   opinion about. Rejected: adapter-on-roots-only, which forces one house
   style per domain.
4. **No chain budget, and the two existing per-file ceilings are kept
   apart.** A root takes `CRAFT_BUDGET`, 130 non-empty lines; a narrowing
   takes `SHEET_BUDGET`, 100. The 30-line gap is not an accident of history:
   `tools/validate_support/common.py:77` states its purpose — a narrowing
   that grew a domain's worth of law would be a second, unregistered domain,
   so its ceiling sits under its parent's. Rejected: one flat ceiling for
   both, which would delete that mechanism and break `orch-design` on
   contact, its craft being exactly 100 lines today. Rejected: a budget on
   the resolved chain, and a scaffold sub-budget tightened as a ratchet —
   real mechanisms, but they buy pressure an author can apply by hand, and
   depth is already bounded by every level being a file someone had to
   write.
5. **`## Scaffolding` is the only marked durability class.** Everything
   outside it is permanent by default, so a fact can never be lost by
   forgetting to tag it. The author's test, per sentence, is
   `docs/library-review.md` criterion 11: would a perfect executor still
   need this? Rejected: tagging incentive guards and facts separately — both
   are permanent, and once something is permanent, why it is permanent
   changes no operation.
6. **Routing picks roots only.** A narrowing is authored: a workflow body or
   a `do`/`judge` call names it. Nothing resolves one automatically. This is
   today's behaviour written down, not a new restriction, and turning
   routing loose on narrowings later is purely additive.
7. **A standard renders no host adapter.** Verified, not assumed:
   `DESIGN.md:388` states the launch prompt "names no skill for the child to
   invoke and no pack for it to resolve", and `skills/kernel/orch-do/SKILL.md`
   reads the craft by the path the prompt hands it. Nothing has ever invoked
   `orch-code-pack`. Twenty rendered adapter files go with the kind: one
   Claude skill, one Codex prompt, one Codex redirect skill and one Grok
   skill for each of the five. Their five `by-name` pointers stay, as a
   sheet's does.

## 1. Frozen goal

At one joined tip on this branch, `uv run --no-project python
tools/run_required.py --no-cache` passes and:

- `contracts/standard.md` is the one owner of the kind, and
  `contracts/pack-signature.md` and `contracts/sheet.md` do not exist;
- `standards/` holds eight items — five roots carrying an `adapter`, three
  narrowings carrying `narrows:` — and `packs/` and `sheets/` do not exist;
- `tickets.py do --standard <name>` resolves the chain by walking
  `narrows:`, pins every level as an ordered `(name, digest)` list, and
  refuses a cycle, a chain deeper than eight, an unresolvable parent, and a
  resolved set carrying zero or two adapters — each proven by a check whose
  failing reading is recorded;
- no shipped file names `pack`, `sheet` or `craft` as a library term, proven
  by a grep whose output is in the frame journal;
- `install.py --dry-run` plans fewer entries than the base commit's 359, and
  the reduction is exactly the twenty rendered host adapters plus the five
  second files the pack collapse removes — the new count and that
  decomposition both recorded in the frame journal.

## 2. Fixed names and shapes

The kind is `standard`. Ring directory `standards`, manifest `STANDARD.md`,
so an item lives at `standards/<name>/STANDARD.md`. The directory holds that
file and nothing else: no `scripts/`, no `requirements.txt`, no `tools.txt`.

Frontmatter:

    name: three-js
    description: <one sentence, at most 140 characters, when to stamp it>
    narrows: javascript        # optional; omit for a root
    adapter: git               # optional; exactly one per resolved set

Sections, and who may carry them:

| section | roots | narrowings |
| --- | --- | --- |
| `## Making` | required | required |
| `## Lens` | required | required |
| `## Vocabulary` | required | optional |
| `## Scaffolding` | optional | optional |
| `## Workspace` | required | refused |
| `## Spec fields` | required | refused |
| `## Stages` | optional | refused |

`## Making` is today's craft prose and today's sheet `## Craft` under one
name. `## Lens` keeps its keying by adapter kind (`git`, `doc`, `evidence`)
and the library-owned `root` and `cut` entries. The three refused sections
are facts about a domain; a narrowing restating one would be a second owner
of it.

The eight shipped items:

    standards/orch-code/       adapter: git             (was orch-code-pack)
    standards/orch-content/    adapter: document-tree   (was orch-content-pack)
    standards/orch-data/       adapter: git             (was orch-data-pack)
    standards/orch-design/     adapter: git             (was orch-design-pack)
    standards/orch-research/   adapter: evidence-store  (was orch-research-pack)
    standards/html-dossier/    narrows: orch-content
    standards/market-brief/    narrows: orch-research
    standards/standard-craft/  narrows: orch-content    (was sheet-craft)

Each adapter above was read off that pack's current `SKILL.md` cells table,
not guessed; re-read them before trusting this list, and a value that
disagrees wins. Note these are workspace-mechanism keys and not the `## Lens`
adapter kinds — `document-tree` keys Lens entries under `doc`, and
`evidence-store` under `evidence`. Roots keep the `orch-` prefix, reserved
for library-owned items in every kind; the three narrowings keep their bare
names, as they have today.

CLI and ticket:

- `--pack P` and `--sheet S` become one repeatable `--standard S`. Each name
  resolves its own chain; chains concatenate in the order written, and a
  standard reached twice is read once, at its first position.
- The ticket's `pack`, `pack_digest` and `sheets` fields become one
  `standards` field carrying the ordered resolved list.
- The finding `sheet-defect` becomes `standard-defect`.
- `scripts/packs.py` becomes `scripts/standards.py`, and
  `packs_support.py` becomes `standards_support.py`.

## 3. Units

### U0 — The contract

Write `contracts/standard.md` as the one owner of everything in section 2:
the kind, its location and anatomy, the frontmatter, the section table, the
six rules below, the two per-file ceilings and the digest. Delete
`contracts/pack-signature.md` and `contracts/sheet.md`, carrying every clause
of theirs that survives — the tighten-only rule and its finding, the digest
over the directory tree re-derived at every door, the refusal of `scripts/`,
`requirements.txt` and `tools.txt`, the `## Lens` keying with its `root` and
`cut` entries, and the pack-signature admission and purity paragraphs. A
clause that does not survive is named in `## Report` with the reason.

The rules, stated once here:

1. A narrowing may only tighten. Where its clause would permit what a
   broader standard forbids, the broader wins and the judge reports
   `standard-defect` — the standard is the defect, not the artifact.
2. Exactly one adapter across a ticket's resolved standards.
3. `narrows:` resolves to a standard in a reachable ring, never revisits a
   name, and terminates within eight hops.
4. At most 130 non-empty lines in a root's manifest and 100 in a
   narrowing's, frontmatter counted — today's `CRAFT_BUDGET` and
   `SHEET_BUDGET`, unchanged in value and in reason. A narrowing's ceiling
   sits under its parent's so that a narrowing cannot grow into an
   unregistered domain.
5. The digest is SHA-256 over the directory tree, pinned at issue and
   re-derived at every door.
6. Routing resolves roots only; a narrowing arrives because an author named
   it.

`## Scaffolding` is defined here and nowhere else: content a perfect
executor would not need, deletable without changing what the standard means,
with everything outside it permanent by default. Cite
`docs/library-review.md` criterion 11 as the test rather than restating it.

No script, item or prose changes in this unit. Its `done` is
`uv run --no-project python tools/validate.py`.

Close `limited`, naming the clause, if a surviving clause cannot be stated
once here without leaving a second owner elsewhere.

### U1 — Resolution and pinning

`scripts/`. Teach the trunk to walk `narrows:`: resolve a stamped name to
its chain, refuse a cycle, a depth over eight and an unresolvable parent,
check that the resolved set carries exactly one adapter, and pin the whole
chain on the ticket as an ordered `(name, digest)` list. `--standard` is
repeatable and dedupes to first position.

The files: `tickets_pins.py` for the pin, `packs.py` and `packs_support.py`
for resolution, `tickets_stamp_generation.py` and `tickets_generations.py`
for the frontmatter the seal reads — note the seal now covers `standards`
where it covered `pack`, `pack_digest` and `sheets` — and
`tickets_commands.py`, `tickets_mint.py` and `tickets_issue.py` for the flag.

Do this **under the old directory names**. Items still live in `packs/` and
`sheets/` when this unit lands; U2 changes their content and U3 moves them.
A `narrows:` field added to a sheet for the sake of a test is this unit's to
add and U2's to keep.

New checks, each with its failing reading recorded: a cycle refuses; a ninth
hop refuses; a missing parent refuses; a resolved set with two adapters
refuses; a set with none refuses; a chain of three pins three digests in
broad-to-narrow order; a standard named twice is read once, at its first
position.

Tests this unit owns: `tests/test_ticket_pins.py` and `tests/test_tickets.py`.

Close `limited`, naming it, if the seal's coverage of the new field cannot
change without invalidating a seal this run itself holds open.

### U2 — The items

Collapse each pack into one manifest. Its `SKILL.md` carries only a name, a
description and a two-row cells table; its `references/craft.md` carries the
prose. The adapter moves to frontmatter, the cells table is deleted, and the
craft body becomes the manifest body under §2's section table — today's craft
sections map across by name where the content already fits, and the maker
guidance becomes `## Making`.

Give the three sheets `narrows:` per §2 and drop their `packs:` field.
Rename `## Craft` to `## Making` in all eight items.

Delete the packs' twenty rendered host adapters — a Claude skill, a Codex
prompt, a Codex redirect skill and a Grok skill for each of the five — and
teach `installer/packages.py` that the kind renders none; its docstring at
`:71` lumps `packs/orch-*` in with skills, which is what mints them. The five
`by-name` pointers stay. The `install.py --dry-run` entry count falls by those
twenty plus the five second files the collapse removes; record the count
before, the count after, and the decomposition in `## Report`.

Do this **under the old directory names**: `packs/` and `sheets/` keep their
paths and U3 moves both into `standards/`. Splitting the move from the
content change is what keeps this unit's diff readable.

Tests and tools this unit owns: `tests/test_validate.py`,
`tests/test_validator.py`, `tests/test_installer_*.py`, and the section-table
rules in `tools/validate.py` and `tools/validate_support/`.

Close `limited`, naming the pack, if a craft section's content does not map
onto §2's table without either loosening a rule or inventing a section.

### U3 — The rename

One mechanical sweep, alone in its wave because it reaches every file the
other three left. `packs/` and `sheets/` become `standards/`; `SKILL.md` and
`SHEET.md` become `STANDARD.md`; `--pack` and `--sheet` become `--standard`;
`scripts/packs*.py` become `scripts/standards*.py`; `sheet-defect` becomes
`standard-defect`; the ticket's fields become `standards`.

Then every prose owner: `docs/vocabulary.md`, whose `pack`, `cell`, `craft`,
`craft section` and `sheet` entries become one `standard` entry plus `root`
and `narrowing`; `docs/custom-workflow-authoring.md`; `docs/pack-authoring.md`,
renamed; `templates/host-block.md`; `skills/kernel/orch-do/SKILL.md` and
`skills/kernel/orch-judge/SKILL.md`; `skills/workflows/*`;
`example-workflows/*`; and `AGENTS.md`, `ARCHITECTURE.md` and `README.md`
where they name a retired term.

`REVIEW-2026-09-03.md` and `REVIEW-2026-09-03-fable.md` are evidence records
of a past state and are not rewritten; the report contract already excludes
them from the link check. Say so in `## Report` rather than editing them.

Verification: `grep -rn "\bpack\b\|\bsheet\b\|\bcraft\b"` over `rules/`,
`contracts/`, `docs/`, `templates/`, `skills/`, `standards/`,
`example-workflows/`, `scripts/`, `tools/` and `installer/` returns only
matches this unit reports and defends — a pack of records, a sheet of paper,
a craft in ordinary prose. Paste the output whole in `## Report`.

Tests: every remaining test file. The host block's 400-word ceiling and
`AGENTS.md`'s 230-word ceiling must both still hold; state both counts.

Close `limited`, naming the file, if a retired term cannot be removed
without a change one of the other units owns.

## 4. Waves

| wave | units | waits on |
| --- | --- | --- |
| 1 | U0 | base |
| 2 | U1, U2 | U0 |
| 3 | U3 | wave 2 |
| 4 | judge, then bounded repair | wave 3 |
| 5 | gate | wave 4 |

U0 goes alone because every other unit reads the names it fixes. U1 and U2
are disjoint — U1 owns `scripts/` and two ticket tests, U2 owns the items,
the installer and the validator — and both work under the old directory
names, so neither blocks the other. U3 goes alone because the rename reaches
every file the other three touched, and a rename racing a content change is
the collision this ordering exists to avoid.

`tests/serial_compat_manifest.json` is the run's one shared derived artifact.
Where a land conflicts on it, the driver — not a child — resolves it by
regenerating at the merged tip with `uv run --no-project python
tools/regen.py`, and records that it did.

## 5. Gate

At the joined tip, once, outside every child:

    uv run --no-project python tools/run_required.py --no-cache
    uv run --no-project python tools/regen.py --check
    git diff --check

Then into the frame journal: the `install.py --dry-run` entry count beside
the base commit's 359, with the reduction decomposed into the twenty host
adapters and the five collapsed second files; U3's retired-term grep; and the
host block and `AGENTS.md` word counts.

One judge, after wave 3, over the joined tip, carrying all four `artifact:`
lines. Where it blocks, one repair `do` handed the `findings:` line verbatim,
then one re-judge; two rounds is the bound.

Then `install.py --accepted-source <tip>` and `orchflows sync`.

## 6. Deferred

- **Routing to narrowings.** Decision 6 keeps them authored. Turning routing
  loose is additive and needs its own evidence about how a router picks
  depth.
- **A ring-level house standard.** A `house:` field in `BUNDLE.md` that
  prepends one standard to every chain resolved from that ring would let a
  house style sit above shipped roots without forking one. Decision 3's
  optional adapter is what makes it possible later; nothing here needs it.
- **The chain budget and the scaffold ratchet.** Decision 4. Revisit when a
  real chain runs deep enough to hurt.
- **Splitting the shipped roots.** Nothing is near a ceiling: against 130,
  the five crafts run 100 (`orch-design`), 94, 91, 83 and 82, and the
  collapse adds only frontmatter. Authoring a narrowing costs its parent no
  lines at all, since a narrowing is its own file with its own budget — the
  pressure only appears when someone wants to *promote* a narrowing's
  content up into a root, and `orch-design` is the one with least room for
  that.
