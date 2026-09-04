# Standard contract

A standard states what a good artifact carries in one domain: the terms,
the workspace, the making guidance and the criteria a judge reads. It is
the library's one unit of domain knowledge, with no second kind beside it
and no second kind below it.

A standard with no `narrows:` is a **root**; one with `narrows:` is a
**narrowing**, and it names exactly one broader standard. That is how
specificity cascades: `three-js` narrows `javascript` narrows `code`. A
ticket stamps one or more names; each resolves its own chain by walking
`narrows:`, and the maker reads the resolved chain broad to narrow while
the judge reads the identical chain at the identical digests. The two are
one format under one set of rules and differ only in the sections the
table below allows them.

A standard is a ring item and nothing else: resolved through
[rings.py](../scripts/rings.py)'s one order, digest-pinned on the ticket
at issue, and read at that digest by the ticket's maker and by its judge.
No host adapter is rendered for one, because nothing invokes one — a
standard is stamped, never called.

## Location and anatomy

Ring directory `standards`, library directory `standards`, manifest
`STANDARD.md`, so a standard lives at `standards/<name>/STANDARD.md` in
whichever ring carries it, and the installer mints the same
`by-name/<name>/STANDARD.md` pointer it mints for every other kind. The
`orch-` prefix is reserved here as it is for every other kind.

The directory holds that manifest and nothing else. A `scripts`
directory, a `requirements.txt` and a `tools.txt` beside it are refused:
a standard is prose, so it declares no dependencies, owns no environment,
and never supplies the document its own well-formedness is judged
against.

## Frontmatter

- `name` — the standard's name, equal to its directory name.
- `description` — one sentence, at most 140 characters, saying when to
  stamp it.
- `narrows` — optional. The one broader standard this one tightens;
  omitted by a root.
- `adapter` — optional. One stable registered workspace mechanism key,
  the typed leaf downstream machinery branches on. It is declared by
  whichever standard introduces the domain, not necessarily the root, so
  a domain-blind standard can sit above two domains without claiming a
  workspace mechanism it has no opinion about.

## Sections

| section | roots | narrowings |
| --- | --- | --- |
| `## Making` | required | required |
| `## Lens` | required | required |
| `## Vocabulary` | required | optional |
| `## Scaffolding` | optional | optional |
| `## Workspace` | required | refused |
| `## Spec fields` | required | refused |
| `## Stages` | optional | refused |

Each `##` heading is a stable anchor, and each binds one thing:

- `## Making` — what the maker does in this domain to reach a
  well-formed artifact.
- `## Lens` — one `###` entry per artifact kind the domain produces:
  what a well-formed artifact of that kind carries, what proves it, and
  which findings block.
- `## Vocabulary` — the domain's terms, defined once for intake,
  execution, and checking alike.
- `## Scaffolding` — below.
- `## Workspace` — identities, isolation, candidate diffs, and conflict
  handling in this domain; the adapter key is declared separately.
- `## Spec fields` — fields a spec must carry for decomposition to
  accept it, read at intake as the checklist a root must satisfy before
  seal.
- `## Stages` — how work proceeds in this domain, as narrative.

The three refused sections are facts about a domain, and a narrowing
that stated one again would own it twice.

## Lens

`## Lens` carries exactly these `###` entries, in this order: `### root`,
then `### cut`, then one entry per artifact kind the resolved set's one
adapter produces — neither a missing kind nor a kind that adapter never
emits. The keys are artifact kinds (`git`, `doc`, `evidence`), which the
adapter registry maps from the workspace mechanism key, not the mechanism
keys themselves. `root` is a frozen goal and `cut` a set of work items
under one; both are library-owned, and the ticket already spells their
identities `root:<id>:<n>:sha256:<digest>` and
`cut:<id>:<n>:sha256:<digest>`.

A making verb makes toward the entry its artifact kind names; a checking
verb reads the same entry as its criteria. A narrowing's entry adds
criteria beside the broader standard's entry of the same key, and a
narrowing that keys no entry the stamp's kind matches adds nothing the
ticket's verbs read. Every verb reads the whole resolved chain and acts
under the sections its skill names.

## Rules

1. A narrowing may only tighten. Where its clause would permit what a
   broader standard forbids, the broader wins and the judge reports
   `standard-defect` — the standard is the defect, not the artifact.
2. Exactly one adapter across a ticket's resolved standards.
3. `narrows:` resolves to a standard in a reachable ring, never revisits
   a name, and terminates within eight hops.
4. At most `STANDARD_BUDGET` words per manifest, frontmatter counted,
   whitespace-separated, equal for a root and a narrowing. Its value is
   1200. Words rather than lines because a line ceiling is gamed by
   writing longer lines.
5. The digest is SHA-256 over the directory tree, pinned at issue and
   re-derived at every door.
6. Routing resolves roots only; a narrowing arrives because an author
   named it.

## Scaffolding

`## Scaffolding` holds content a perfect executor would not need, and it
can be deleted without changing what the standard means. Everything
outside it is permanent by default, so no fact is lost by forgetting to
tag it. Whether a sentence belongs there is
[library-review.md](../docs/library-review.md) criterion 11's test,
applied sentence by sentence; this file states no version of that test of
its own.

## Identity

Rule 5's digest covers every file in the standard's directory: each
file's path relative to that directory, sorted, with its bytes. Relative
to the directory and never to the repository, because the path a standard
was found at is an observation: one shipped in two rings must digest the
same, or the pin refuses the shadow it exists to catch. The ticket pins
that digest at issue and every later door re-derives it, so a standard
that changed under a sealed assignment — or a nearer ring that came to
shadow it — is a refusal rather than a substitution.
[work-item.md](work-item.md) owns the ticket fields that carry the pins;
[tickets_pins.py](../scripts/tickets_pins.py) is the one resolver, hasher
and verifier for them.

## Admission

A domain earns a root for materially different artifact evidence or
workspace semantics. It earns a narrowing when one assignment needs that
domain tightened — a house style, a client's report shape, a family of
checks a run wants applied — and the alternative would be forking the
root or editing prose every other run reads. Prose earns a section only
when its content differs between standards and no other section already
owns that content.

Purity: a standard body contains no delegation language, stop states,
conditionals, or Return contract. The validator states its mechanical
checks; the authoring guide owns the remaining judgment.

Sharing constraints, checked at review:

- Every candidate form emitted by slicing is expressible in
  `## Workspace`.
- Every domain term another section uses is defined once in a
  `## Vocabulary` somewhere on the resolved chain, or inline in the
  section that uses it.

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

### `standard_root_sections`

| field | required | declared values |
| --- | --- | --- |
| `Making` | yes | — |
| `Lens` | yes | — |
| `Vocabulary` | yes | — |
| `Scaffolding` | no | — |
| `Workspace` | yes | — |
| `Spec fields` | yes | — |
| `Stages` | no | — |

### `standard_narrowing_sections`

| field | required | declared values |
| --- | --- | --- |
| `Making` | yes | — |
| `Lens` | yes | — |
| `Vocabulary` | no | — |
| `Scaffolding` | no | — |

<!-- END GENERATED T0 SHAPES -->
