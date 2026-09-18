# Shared processes

Small composable workflows for decisions and bounded revision. Task details come from the prompt; quality and taste come from selected guidance. Ordinary task allocation, fan-out, gathering and staffing come from core.

| Component | Contract |
| --- | --- |
| [compare-candidates](skills/compare-candidates/SKILL.md) | Compare stable alternatives under common criteria; return evidence and preference, without adoption or edits |
| [review-revise-once](skills/review-revise-once/SKILL.md) | Review independently, repair at most once, verify, and distinguish reviewed and delivered states |

The top-level orchestrator dispatches all assignments. Comparison uses one independent comparer. Review-and-revision uses core's standard pattern: one independent whole-result reviewer, at most one coordinated repair pass and required verification. Repair staffing stays flexible.

## Use and dependencies

Requires Orchflows core 0.10.0+ and native child delegation. This package adds no runtime, domain guidance or required tools. See [library context](references/library-context.md).

From the checkout:

```sh
python scripts/orchflows.py setup --example shared
```

Register the package with the intended host using core `docs/hosts.md`; a copied file is not proof of native availability. All skills are manual-only by default. Use `$shared:compare-candidates` in Codex or `/shared:compare-candidates` in Claude, with the corresponding syntax for `review-revise-once`. Honor host restrictions on composed calls. Setup installs no transitive library dependencies.

Example requests:

> Compare these supplier proposals against this brief. Identify missing evidence and comparable total costs. Recommend only when the evidence supports it; do not place an order.

> Review this operating report against its source records, then revise it once and check the changed figures. Preserve the original report and review findings. Use writing guidance and this company's reporting extension.

Design loop uses comparison for `test-increment`. Personal briefs and reports can use review-and-revision on an existing candidate. Their evidence requirements and domain rules remain with their recipes; the orchestrator applies component instructions directly.

## Build a personal composition

For example, save a decision-brief workflow in `~/.orchflows/libraries/personal/skills/decision-brief/SKILL.md`:

> Resolve the question, supplied proposals and decision criteria. Use shared:compare-candidates on the proposals. Write a recommendation from its actual evidence, retaining uncertainty or no eligible choice. Use shared:review-revise-once on that draft and the source records. Return the recommendation, comparison, original review, delivered revision and gaps. Stop after this one revision pass; take no external action.

Declare `shared` as a dependency and select the applicable guidance. Keep criteria and writing taste in personal guidance, current inputs in the invocation, and metadata with the personal library. Save the process and stopping conditions; leave staffing to the orchestrator.

## Validation

[Trials](trials/README.md) distinguish earlier component checks from the current builder-to-personal-library acceptance scenarios. Run from an unrelated workspace with declared dependencies and ordinary inputs. Metadata checks do not establish behavior or cross-host portability.
