# Standard contract

A standard is nonempty prose describing quality in one domain. Makers and
judges read its complete text, so its guidance may use any clear Markdown
layout. Headings help people navigate; their presence or spelling does not
decide whether the standard is complete.

A standard with no `narrows:` is a **root**. One with `narrows:` is a
**narrowing** and names one broader standard whose guidance it tightens. A
ticket may stamp several standards as orthogonal guidance. Each named item
expands its optional base broad to narrow, then the resolver concatenates the
chains in the caller's order and removes repeated identities after their first
appearance. The maker and judge read that same ordered set at the same digests.

A standard is a ring item resolved through [rings.py](../scripts/rings.py)'s
order, pinned when a ticket is issued, and rechecked at later doors. Nothing
invokes it and no host adapter is rendered for it: a standard is stamped,
never called.

## Location and anatomy

The ring and library directory is `standards`; the manifest is `STANDARD.md`.
A standard therefore lives at `standards/<name>/STANDARD.md` in whichever
ring carries it. Its directory may include prose references for optional
depth, but all guidance required for the assignment stays in the manifest
passed to both roles.

Executable helpers and dependency declarations are invalid here. The
validator refuses the conventional script and requirements locations. A
standard owns no environment and never supplies the contract used to judge
its own well-formedness.

## Frontmatter

- `name` — required; equal to the directory name.
- `description` — required; at most 140 characters, saying when to stamp it.
- `narrows` — optional; the one broader standard this item tightens.
- `adapter` — optional legacy workspace hint. If present, it names a
  registered mechanism. Composition ignores this observation; workspace
  selection consults it only when no explicit adapter or concrete target
  settles the mechanism.

## Guidance

The manifest answers the domain questions that matter. Authors normally ask:

- Which terms need fixed meanings?
- What result and constraints must an outline preserve?
- What is the smallest useful slice?
- Which craft practices lead a maker toward that result?
- What evidence and defects should a reviewer examine?

Those are authoring questions, not five required headings. A concise paragraph
may answer all of them. A longer standard may use headings suited to its
readers. Empty text or headings without substantive guidance are refused.

The optional legacy `## Lens` layout remains readable. When present, it
appears once and contains uniquely named, nonempty `###` entries. Entry names
help readers locate criteria; the validator does
not infer semantic coverage, workspace selection, or supported artifact kinds
from them. Makers and judges still read the full standard rather than a
machine-selected subsection.

## Rules

1. A narrowing only tightens. Where its guidance contradicts its base,
   reviewers classify the narrower guidance itself as `standard-defect`.
2. `narrows:` resolves to one standard in a reachable ring, never revisits a
   name, and terminates within eight hops.
3. Explicitly named standards are orthogonal guidance. Resolution preserves
   caller order and deduplicates a shared base at its first appearance.
4. Each manifest is at most `STANDARD_BUDGET` whitespace-separated words,
   frontmatter included. `STANDARD_BUDGET` is 1200 for roots and narrowings.
5. The digest is the canonical `standard` item-tree identity over every file
   in the directory and is pinned at issue and re-derived at every door.
6. Adapter hints are compatibility observations. Their absence, repetition,
   or disagreement does not change the resolved standard set.

## Identity

The canonical digest frames `standard` plus every file's directory-relative
path, normalized bytes, and byte length in sorted path order. Repository and
ring locations are observations outside the identity, so the same standard
shipped in two rings has one digest. Adding, deleting, renaming, or changing a
file moves the digest. [work-item.md](work-item.md) owns the ticket fields;
[tickets_pins.py](../scripts/tickets_pins.py) re-derives their pins.

## Admission

A domain earns a root when its quality guidance materially differs. It earns a
narrowing when recurring work needs that guidance tightened, such as a house
style or a client-specific review bar. Independent concerns remain separate
standards that a ticket lists together.

Purity: a standard body contains no delegation flow, stop states, or Return
contract. Validation checks identity, consumed frontmatter, nonempty guidance,
links, budget, optional Lens structure, and executable-file refusals. It does
not decide whether prose covers a domain well; authors and reviewers own that
judgment through [standard authoring](../docs/standard-authoring.md).

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/standard.md`. Rendered T0 shape; declaration drift is a validation error.

### `standard_frontmatter`

| field | required | declared values |
| --- | --- | --- |
| `name` | yes | — |
| `description` | yes | — |
| `narrows` | no | — |
| `adapter` | no | — |

<!-- END GENERATED T0 SHAPES -->
