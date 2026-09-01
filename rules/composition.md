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
   backticked. Markdown links to another package's `references/` are
   file dependencies, not call edges.
3. The call graph is acyclic. Recursion, including mutual, is expressed
   by an engine's bounded iteration, never by a call cycle.
4. Every callable skill ends with `Return` naming its output fields,
   `[]` for empty collections. A change to a Return shape is breaking.
5. Anatomy: frontmatter (`name` = folder name, `description` within
   the character budget `common.py`'s `DESCRIPTION_BUDGET` already
   enforces, `role` ∈ {planner, worker, none} — pack SKILL.md carries
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
9. Generic skills (kernel, workflows) never name a
   domain; how they reach domain facts is
   [contracts/pack-signature.md](../contracts/pack-signature.md)'s. A
   generic body may name the skill the stamped pack's cell binds, only
   in apposition to the cell reference that binds it.
10. Every `Require:` item rides a named T0 carrier — a field a T0
    contract defines, never bare prose; the caller supplies each
    callee's `Require` item by that name. A dispatchable unit's
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
