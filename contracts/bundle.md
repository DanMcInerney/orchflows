# Bundle contract

What a bundle is, and which ring an item belongs in, is
[custom-workflow-authoring.md](../docs/custom-workflow-authoring.md)'s. This
contract owns one file in it: `BUNDLE.md`, the bundle's own manifest, saying
what the bundle is called, which revision of it this is, and which other
bundles it needs to work.

The manifest is a declaration, never a fetch instruction executed on read:
`orchflows add` reads it after the clone it was asked for, resolves the
requirements it names into pins, and stops. Nothing here runs code, and
nothing here grants trust — an imported bundle's content is still read
through [rings.py](../scripts/rings.py)'s order and its project content still
answers to the trust ledger.

## Location

Inside the bundle directory, beside that bundle's item directories rather
than inside one of them. The home ring's own manifest is therefore at the
root of the home ring, a project's is inside the project's bundle directory,
and a cloned bundle's sits where the resolver finds that clone's items.
There is no second location and no search. `rings.BUNDLE_MANIFEST` is the
filename's one owner, as `rings.BUNDLE_DIR` is the directory's.

A bundle without a manifest is a bundle with no requirements. Every bundle
published before this file existed is one, so an absent manifest is a fact,
never a refusal.

## Frontmatter

- `name` — the bundle's name. A published bundle's is how consumers speak of
  it; the home ring's is its owner's choice.
- `version` — a tag or a date. It says which revision of the bundle this is,
  and it is prose: nothing resolves a pin through it.
- `requires` — a list of `<git-url>@<pin>` references, each naming one bundle
  this one needs. A tag or a full commit SHA is a pin; a branch name is not.

The body below the frontmatter is free prose: what the bundle is for, who
owns it, what a consumer gets.

## The closure

`orchflows add <git-url>@<pin>` clones the named bundle, reads its manifest,
and follows `requires` depth-first, cloning and pinning each bundle it
reaches. The whole closure lands in `imports.lock` in one write, so an add
either pins everything it reached or pins nothing: a refusal removes the
clones that add made.

Two refusals, each naming the manifest that carries the offending line:

- **unpinned** — a `requires` entry that is not `<git-url>@<pin>`, or whose
  pin is a branch name the remote does not publish as a tag. The pin law is
  [orchflows_home.py](../scripts/orchflows_home.py)'s one law, and a
  requirement is held to it exactly as the reference a person typed is.
- **cycle** — a `requires` entry naming a bundle already open on the path
  the manifest was reached by. A cycle has no closure to pin.

A bundle already pinned at the same pin is reached once and cloned once: a
diamond is not a cycle. A bundle already pinned at a *different* pin is a
refusal naming both pins, because one imports directory holds one clone of a
bundle and silently keeping the older pin would answer a requirement nobody
declared.

`orchflows sync` restores that closure: it clones what `imports.lock` names,
reads each restored bundle's manifest, and pins and clones any requirement
the lock does not already carry. Restore is a recovery path and never fails
the whole sync: a requirement it cannot pin is reported against the bundle
that declared it, and a bundle already restored is never visited twice, so a
cycle terminates here rather than refusing. Authoring-time refusal belongs to
`add`.
