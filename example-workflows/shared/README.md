# Shared processes

Composable procedures for decisions and bounded revision. Task details come from the prompt; quality and taste come from selected guidance. Core defines execution rules; the coordinator staffs the work.

| Component | Contract |
| --- | --- |
| [compare-candidates](skills/compare-candidates/SKILL.md) | Compare stable alternatives under common criteria; return evidence and preference, without adoption or edits |
| [review-revise-once](skills/review-revise-once/SKILL.md) | Compatibility entry to core `orch-review-revise-once`: review independently, repair at most once, verify, and distinguish reviewed and delivered states |

Procedures compose to any depth in one coordinator. Loading a nested procedure does not launch an agent, add a review or reset a bound. Only the top-level coordinator dispatches agents; children do not delegate. Comparison uses one independent comparer. The compatibility entry applies core review-and-revision in that same coordinator, adding no stage: one independent whole-result review, at most one coordinated repair pass and required verification. Ordinary drafting and repair staffing stay flexible.

Pass applicable guidance, constraints and settings through each call. Keep local guidance and output locations scoped to that work; they do not overwrite the parent or leak into siblings. Makers and reviewers share the substantive quality criteria, with role-specific instructions where supplied.

## Use and dependencies

Requires Orchflows core 0.11.0+ and native child delegation. This package adds no runtime, domain guidance or required tools. See [library context](references/library-context.md).

From the checkout:

```sh
python scripts/orchflows.py setup --example shared
```

Register the package with the intended host using core `docs/hosts.md`; a copied file is not proof of native availability. All skills are manual-only by default. Use `$shared:compare-candidates` in Codex or `/shared:compare-candidates` in Claude, with the corresponding syntax for `review-revise-once`. Resolve dependencies through supported native skills or supplied package paths. Setup installs no transitive library dependencies.

Example requests:

> Compare these supplier proposals against this brief. Identify missing evidence and comparable total costs. Recommend only when the evidence supports it; do not place an order.

> Review this operating report against its source records, then revise it once and check the changed figures. Preserve the original report and review findings. Use writing guidance and this company's reporting extension.

Design loop uses comparison for `test-increment`. Personal briefs and reports can use review-and-revision on an existing candidate. Their evidence requirements and domain rules remain with their recipes; the orchestrator applies component instructions directly.

## Build a personal composition

For example, save a decision-brief workflow in `~/.orchflows/libraries/personal/skills/decision-brief/SKILL.md`:

> Resolve the question, supplied proposals and decision criteria. Use shared:compare-candidates on the proposals. Write a recommendation from its actual evidence, retaining uncertainty or no eligible choice. Use shared:review-revise-once on that draft and the source records. Return the recommendation, comparison, original review, delivered revision and gaps. Stop after this one revision pass; take no external action.

Declare `shared` as a dependency and select the applicable guidance. Keep criteria and writing taste in personal guidance, current inputs in the invocation, and metadata with the personal library. Save the process and stopping conditions; leave staffing to the orchestrator.

## Validation

[Trials](trials/README.md) include builder-to-personal-library scenarios and a new [composition fixture](trials/composition/request.md) for nested procedures, scoped guidance and the compatibility entry. The new fixture has not yet been run. Earlier observations remain historical evidence. Run from an unrelated workspace with declared dependencies and ordinary inputs; metadata checks do not establish behavior or cross-host portability.
