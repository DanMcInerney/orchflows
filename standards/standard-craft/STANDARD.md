---
name: standard-craft
description: Stamp when the document being written is itself a standard - a narrowing of some broader one.
narrows: orch-content
---

# standard-craft

## Making

A narrowing is a standard that tightens exactly one other, resolved through
the ring order and read at a pinned digest by a ticket's maker and by its
judge ([contracts/standard.md](../../contracts/standard.md)). Those two are
the only readers. Write for them.

- **Knowledge only.** It says what good looks like in one narrowed
  domain. It carries no ordered procedure, nothing to execute, and nothing
  to install - a thing that runs is a skill, and an order of steps is a
  workflow. The directory holds prose and nothing else.
- **Additive and tighten-only.** Every clause narrows a requirement the
  broader standard already makes, or adds one it leaves open. Where a
  clause would permit what the broader one forbids, the broader one wins
  and the narrowing is the defect.
- **Bounded to the one it names.** `narrows:` names the single standard
  this was written against, and the `## Lens` entries are keyed by the
  artifact kind that standard emits. Say nothing about a standard you
  never read.
- **Every claim traceable.** A clause rests on a source it names, or on a
  fact the stamping ticket's Context carries. A
  house rule with no source behind it is an opinion wearing a pin, and the
  pin is what makes it binding on every later run.
- **Every criterion provable.** A `## Lens` entry names the reading that
  settles it: a file, a count, a figure, a check the library already runs.
  A criterion nobody can execute is a preference, and a judge asked to
  apply one either invents a rule or ignores the entry.
- **The ceiling is design pressure.** One word ceiling over the whole
  manifest, the same number a root is held to. At the wall, cut the
  weakest clause and record the cut; a narrowing that needs more room is
  carrying a domain's worth of law and belongs in a root.

## Lens

### doc

- Traceability: every `## Making` claim traces to a source it names or to
  a fact the ticket's Context carries; an untraceable clause is a finding
  whatever its merit.
- Provability: every `## Lens` entry names what settles it. An entry
  resting on an adjective is a finding.
- Knowledge only: no ordered procedure, no thing to execute, no declared
  dependency anywhere in the standard, and nothing executable in its
  directory.
- Tighten-only: no clause loosens the broader standard's; a loosening
  clause is reported as `standard-defect`, against the narrowing rather
  than against any artifact made under it.
- Bounds: name equals the directory, the description is one sentence
  saying when to stamp it, `narrows:` resolves, the Lens keys are kinds
  the broader standard emits, and the manifest holds the word ceiling -
  the library's own validator is what reads all six.
