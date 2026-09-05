# Composition

1. A skill is one directory owning one `SKILL.md` contract. Kind by
   out-edges: a primitive calls no skill; a composite calls one or
   more. Kernel skills are always primitives (validator-enforced);
   workflows may be either. A workflow declares
   `disable-model-invocation: true` in its own frontmatter: its prose runs
   as orchestrator reasoning rather than inside a sealed child prompt, so it
   is invoked by name and never on a host's reading of a description.
2. Every resolved backticked skill name in a body is a call edge. Name
   each call once, at its prose call site, with the exact backticked
   name; mention a skill without calling it in plain text, never
   backticked. Markdown links to the owning package's resources are file
   dependencies, not call edges; a link outside the package may cite
   canonical library law only, as §16 defines.
3. The call graph is acyclic. Recursion, including mutual, is expressed
   by an engine's bounded iteration, never by a call cycle.
4. Every callable skill ends with `Return` naming its output fields,
   `[]` for empty collections. A change to a Return shape is breaking.
5. Anatomy: frontmatter (`name` = folder name, `description` within
   the character budget `common.py`'s `DESCRIPTION_BUDGET` already
   enforces, `role` ∈ {planner, worker, none} — standard SKILL.md carries
   no `role`), then `Require:`, procedure, `Never:`, `Return:`. Body
   budgets and their counting are
   [token-economy.md](token-economy.md) §11's; what the body holds is
   its §6's.
6. Admission: a new skill's contract must be expressible from existing
   skill contracts; otherwise it is a kernel candidate and must show
   that omitting it forces another skill to inline its judgment. Two
   skills whose contracts match the same task is a defect — one owner
   per judgment.
7. Parallel branches may touch the same paths. Isolation preserves candidates;
   the join mechanically detects actual overlap and ordinary Git conflicts.
8. Every failure path returns partial results plus the evidence
   gathered; work is never silently discarded.
9. Generic skills (kernel, workflows) never name a domain; each callable
   reaches domain facts through the standard and narrowing chain its caller
   stamps, under [contracts/standard.md](../contracts/standard.md). A generic
   workflow names the standard on the call that needs it rather than copying
   domain criteria into its body.
10. A machine-consumed `Require:` value rides the named field or protocol
    envelope its T0 contract defines. A workflow's semantic inputs remain
    ordinary prose carried in the call's Goal, Details, and Context; an author
    does not add a T0 field for each idea. The caller supplies every required
    input through the carrier appropriate to it. A dispatchable unit's
    `Return:` leads with the result envelope per
    [contracts/result.md](../contracts/result.md); evaluators are
    exempt. A `Return:` item with no consumer or
    carrier is a defect.
11. `Require:`, `Never:`, and `Return:` are binding contract; the
    procedure between them is the default method. An executor may
    substitute its own method only where every Require, Never, Return,
    bound, and Goal still holds; a substitution never relaxes a deterministic
    repository gate or distorts the
    record a Return field is contracted to carry — disagreement,
    rationale, and contradiction are recorded as found — and is named
    in the result's `## Report`.
12. A standard and an applied skill are stamped by the caller on one ticket
    and read only by that ticket's maker and its judge, each at the digest
    the ticket pins. A stamped standard resolves its whole `narrows:` chain,
    and every narrowing in it only tightens the one it names
    ([contracts/standard.md](../contracts/standard.md)); an applied skill
    is the method inside the kernel contract the ticket's `executor` names,
    which still binds Require, Never and Return. Neither is a call edge:
    nothing invokes them.
13. Recurrence. A step that holds at least one callable and recurs across
    two or more workflows, or whose run deserves its own journal, is a
    reusable workflow invoked by name; a step with no callable of its own
    is a sentence in the calling prose; a recurring sentence's wording is
    an idiom, worded once in
    [custom workflow authoring](../docs/custom-workflow-authoring.md) and
    quoted from there.
14. Placement. An item lives in the innermost ring that contains every
    caller: one project, the project ring; two, the home ring; other
    people, a bundle they import.
15. A top-level workflow is the public owner of its directory. It may keep
    package-private items at `workflows/<name>/workflows/<helper>/SKILL.md`,
    `skills/<method>/SKILL.md`, and `standards/<standard>/STANDARD.md`, with
    ordinary resources and scripts beside them. These nested items resolve
    by name for calls owned by that public workflow, before the outer rings,
    and never enter global inventory or generated host adapters. A call to a
    top-level public workflow starts that workflow's scope; a call to a
    private helper keeps its enclosing public scope. There is no export
    manifest: an ordinary top-level ring item is public and a nested one is
    private.
16. One workflow-package identity covers the public body and every contained
    helper, standard, skill, script, fixture, and reference. The frame and
    each child pin that public owner, its whole-tree digest, and the contained
    workflow entry they read. Resolution rechecks the owner's ordinary ring
    trust and contains every private path below it; no path supplied by prose
    can establish scope. Local resource links stay in the package. Links out
    may cite only canonical library law under `contracts/`, `docs/`, or
    `rules/`. Static admission checks literal Orchflows commands and says
    when dynamic or implied prose calls remain unchecked; prose remains the
    workflow's control flow.
