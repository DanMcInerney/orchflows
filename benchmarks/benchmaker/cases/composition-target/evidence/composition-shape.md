# The workflow file shape, at toy scale

The target of this case is a workflow file: a named pipeline over
dispatchable units. The shape below is `contracts/composition.md` cut
down to what a two-or-three-step toy pipeline needs, with the same
fields carrying the same meanings. It is the contract a workflow file
here must satisfy.

## Frontmatter

- `name` — the identity the file is dispatched under.
- `description` — at most 140 characters; the routing surface.
- `entry` — one of `routed`, `named`, `scheduled`.

## Require

One line naming what the caller must supply before the first step runs.

## Steps

One bullet per step, in this form:

    - <id> — `<unit>` — produces `<artifact>`: <what the artifact holds>

`<id>` is lowercase, hyphenated, unique in the file. `<unit>` is the
skill the step dispatches. `<artifact>` is the identity the step
produces — the toy-scale stand-in for the result envelope a real step
returns, and the thing every later field refers to. Two steps minimum;
no two steps produce the same artifact.

## Edges

One line, one or more edges separated by `; `:

    Edges: seq <id> → <id> — carries `<artifact>`

The carried artifact is the predecessor's produced artifact: that is
what makes the edge a chain rather than an ordering. Every step is on
the chain, each step has at most one predecessor and one successor, and
exactly one step starts it.

## Invariants

A `Never:` block, one bullet per step:

    - <id> — <what that step must never do>

Every declared step id appears as a bullet subject. A step no invariant
binds is the admission failure `contracts/composition.md` names: the
step runs under no stated law, so nothing in the file says what would
make its output wrong.

## Done check

One paragraph: the end-to-end oracle over the final artifact. It names
the terminal step's artifact and states a predicate over its content. A
chain of individually gated steps has no gate over the whole; this field
is that gate. Restating step status ("every step returned complete") is
not a done check — it reports that the pipeline ran, which is already
known, and says nothing about what it produced.

## Return

Leads with `status, result`, as any skill's Return does.
