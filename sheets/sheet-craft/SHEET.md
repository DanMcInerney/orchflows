---
name: sheet-craft
description: Stamp when the document being written is itself a sheet - extra craft stamped beside a pack.
packs: [orch-content-pack]
---

# sheet-craft

## Craft

A sheet is extra craft one ticket stamps beside its pack, resolved through
the ring order and read at a pinned digest by that ticket's maker and by its
judge ([contracts/sheet.md](../../contracts/sheet.md)). Those two are the
only readers. Write for them.

- **Knowledge only.** A sheet says what good looks like in one narrowed
  domain. It carries no ordered procedure, nothing to execute, and nothing
  to install - a thing that runs is a skill, and an order of steps is a
  workflow. The directory holds prose and nothing else.
- **Additive and tighten-only.** Every clause narrows a requirement the
  named packs' craft already makes, or adds one the craft leaves open.
  Where a clause would permit what a craft forbids, the sheet is the
  defect and the craft wins.
- **Bounded to the packs it names.** `packs:` lists the packs this sheet
  was written against, and its `## Lens` entries are keyed by the artifact
  kinds those packs emit. A sheet says nothing about a craft it never read.
- **Every claim traceable.** A clause rests on a file in the sheet's own
  `references/`, or on a fact the stamping ticket's Context carries. A
  house rule with no source behind it is an opinion wearing a pin, and the
  pin is what makes it binding on every later run.
- **Every criterion provable.** A `## Lens` entry names the reading that
  settles it: a file, a count, a figure, a check the library already runs.
  A criterion nobody can execute is a preference, and a judge asked to
  apply one either invents a standard or ignores the entry.
- **The ceiling is design pressure.** A hundred non-empty lines, beside the
  craft budget and under it. At the wall, cut the weakest clause and record
  the cut; a sheet that needs more room is carrying a pack's worth of law
  and belongs in a pack.

## Lens

### doc

- Traceability: every `## Craft` claim traces to a named source in
  `references/` or to a fact the ticket's Context carries; an untraceable
  clause is a finding whatever its merit.
- Provability: every `## Lens` entry names what settles it. An entry
  resting on an adjective is a finding.
- Knowledge only: no ordered procedure, no thing to execute, no declared
  dependency anywhere in the sheet, and nothing executable in its
  directory.
- Tighten-only: no clause loosens the named packs' craft; a loosening
  clause is reported as `sheet-defect`, against the sheet rather than
  against any artifact made under it.
- Bounds: name equals the directory, the description is one sentence
  saying when to stamp it, `packs:` resolves, the Lens keys are kinds
  those packs emit, and the manifest holds the line ceiling - the
  library's own validator is what reads all six.
