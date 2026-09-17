# Shared processes

Small composable workflows for decisions and bounded revision. Task details come from the prompt; quality and taste come from selected guidance. Ordinary task allocation, fan-out, gathering and cumulative bounds come from core.

| Component | Contract | Standalone default |
| --- | --- | --- |
| [compare-candidates](skills/compare-candidates/SKILL.md) | Compare stable alternatives under common criteria; return evidence and preference, without adoption or edits | One reviewer, one child start |
| [review-revise-once](skills/review-revise-once/SKILL.md) | Review independently, repair at most once, verify, and distinguish reviewed and delivered states | One reviewer and at most one fresh fixer; two child starts |

A caller can supply a broader allocation for one round, or a smaller one with an existing maker or caller-owned repair. The parent retains its process requirements and remaining allowance. Defaults do not replenish a composed run's budget. These are process choices, not a global one-worker/one-reviewer restriction.

## Use and dependencies

Requires Orchflows core 0.8.0+ and native child delegation. This package adds no runtime, domain guidance or required tools. See [library context](references/library-context.md).

From the checkout:

```sh
python scripts/orchflows.py setup --example shared
```

Register the package with the intended host using core `docs/hosts.md`; a copied file is not proof of native availability. All skills are manual-only by default. Use `$shared:compare-candidates` in Codex or `/shared:compare-candidates` in Claude, with the corresponding syntax for `review-revise-once`. Honor host restrictions on composed calls. Setup installs no transitive library dependencies.

Example requests:

> Compare these supplier proposals against this brief. Identify missing evidence and comparable total costs. Recommend only when the evidence supports it; do not place an order.

> Review this operating report against its source records, then revise it once and check the changed figures. Preserve the original report and review findings. Use writing guidance and this company's reporting extension.

The design-loop example uses comparison for `test-increment`; benchmaker uses review-and-revision after its independent pilot. Their required counts and stronger domain rules remain with their recipes. These consumers do not wrap the component in another worker.

## Build a personal composition

For example, save a decision-brief workflow in `~/.orchflows/libraries/personal/skills/decision-brief/SKILL.md`:

> Resolve the question, supplied proposals and decision criteria. Use shared:compare-candidates on the proposals. Write a recommendation from its actual evidence, retaining uncertainty or no eligible choice. Use shared:review-revise-once on that draft and the source records. Return the recommendation, comparison, original review, delivered revision and gaps. Stop after this one revision pass; take no external action.

Declare `shared` as a dependency, select the applicable guidance and save finite defaults. For this example, three child starts cover comparison, review and a fresh fixer; direct drafting and permitted caller-owned repair need no child. If drafting is delegated, provide its allowance too. Keep criteria and writing taste in personal guidance, current inputs in the invocation, and package metadata with the personal library.

## Validation

[Trials](trials/README.md) cover an existing example's comparison, a personal office-work composition, and exhausted allowance. Run from an unrelated workspace using declared package roots, without the authoring discussion or expected answers. Metadata checks do not establish behavior or cross-host portability.
