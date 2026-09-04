---
name: orch-code-pack
description: Domain pack for executable artifacts — code evidence, git workspace. Stamp when the deliverable is code.
adapter: git
---

# orch-code-pack

## Making

The shape principles every domain shares are
[rules/token-economy.md](../../rules/token-economy.md) §10's.

## Vocabulary

- **seam** — a public boundary where behavior is observable and
  testable; completion checks live at seams.
- **tracer** — a thin end-to-end slice proving the seams early, before
  anything widens.
- **idiom** — the surrounding code's existing names and patterns; new
  code reconciles to them, never imports a foreign style.

## Workspace

git: identities are commits; isolation is a branch or worktree per
candidate; changes are ordinary diffs; Git conflicts and shared derived
artifacts resolve once at the join through the conflict owner.

## Spec fields

target repository; standards owner by pointer; observable result

## Lens

### root

#### What a frozen code root carries

- Observable behavior at a seam, never the modules that will carry it.
- The failure paths the result must survive: an executor's checks answer
  to Goal alone, so an unstated path is an unchecked one.
- A pointer to the standards owner. The only oracle a root may freeze is its
  own `done` command; every other check is the executor's.
- A claim the root makes about the target tree's state — which module carries
  a behavior, which checks read a name it retires, what a constant is — is
  carried as the command that derives it, never as a recalled fact. The
  intake question "What must keep working that this change could plausibly
  break?" is answered by that command's output.

#### Worth asking at intake

- Which seam makes the outcome observable from outside the change?
- What must keep working that this change could plausibly break?
- Does a tracer slice exist that proves those seams before anything widens?
- Is the target repository, and its baseline revision, actually settled?

#### Exemplar policy

Cite a module by path and revision, then list each property the imitation has
to carry: idiom, check style, layering. "Look like that file" lists none of
them, so it grants nothing.

### cut

Acceptance-first tickets: every seam whose observable result is already
determined by the root Goal is its own item on the first frontier. Cut a
tracer — one thin end-to-end crossing, taken first and widened after — only
for the riskiest seam the Goal leaves unproven.

- Dependency edges exist only where one unit's seam is another's input.
- A Goal ordering growth into a named file prices that file against the
  standards owner's bounds at cut time — a measurement command in Context,
  never a relayed count — test modules included.

### git

- Correctness: does the revision satisfy the spec's acceptance,
  including its failure paths, not only the happy path?
- Contract fidelity: does every public seam still honor its declared
  Require/Return shape for callers outside this revision?
- Diff: does every changed line contribute to Goal inside the spec's
  stated surface — nothing incidental swept in, no check weakened to
  reach green?
- Shape: does the revision hold the idiom and simplification bar above
  rather than import a foreign pattern? The standards owner is a
  citable violation class.

Record the candidate revision, derived test identities with their failing and
passing readings — a check honestly green on arrival records a can-fail reading
instead, taken without mutating the tree under test — affected workspace-check
readings, and uncovered behavior.

Weigh in this order — a shape finding never outranks a correctness
finding.

- Locality: a module owns one concern at one-read size (~100–500 lines);
  past the band presume a second concern — split at a seam, never shave
  prose to fit. Grow sideways: a new module at a seam, never girth.
- Explicit over clever: static, followable call sites; no runtime
  registries or metaprogrammed dispatch — they blind exact search and
  language servers at once.
- Failure is loud and typed: a silent fallback hides the red a later
  agent needs.
- Comments state only what code cannot: the module's opening contract,
  invariants, ordering constraints, why-not-the-obvious.
- Test economy: one deterministic, parallel-safe check per behavior at
  its seam; internals earn none, a check repeating covered behavior is
  deleted, and suite time is paid by every future change.
- Checks pin shapes, never sentences: assert a field, a set, a count
  by kind, or a verdict — never an owner file's prose; a ratchet
  counts the kind it was written for. A check reading an owner file
  reads a stable anchor — a heading, a backticked name, a fenced
  command — and its wrong result drops the fact, not the anchor,
  which would only prove the grep.

## Stages

- Implement at seams, reconciling with the surrounding idiom; take the
  tracer first where Goal leaves a seam unproven.
- Checks answer to Goal, never to the code: each acceptance behavior
  carries a check derived from the ticket's Goal, its failing reading
  recorded — authored at any point, weakened at none.
- For conflict or repair work, read both candidate diffs and the accepted
  blocker ledger; resolve only evidence-backed overlap and record the
  resulting identity.
- A clean repair is an explicit empty-set proof, not an unrecorded no-op.
- Conclude by recording the commit hash, commands run, and outstanding caveats.
