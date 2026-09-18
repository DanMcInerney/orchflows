# Shared comparison

A reusable workflow for comparing stable alternatives under the caller's criteria. Task details and quality guidance come from the caller.

| Component | Result |
| --- | --- |
| [compare-candidates](skills/compare-candidates/SKILL.md) | Evidence, coverage gaps and a supported preference; no adoption or candidate edits |

## Use and dependencies

Requires Orchflows core 0.12.0+ and native independent review. See [library context](references/library-context.md). Install from the checkout:

```sh
python scripts/orchflows.py setup --example shared
```

Register the package with your host using core `docs/hosts.md`. Invoke `$shared:compare-candidates` in Codex or `/shared:compare-candidates` in Claude, with the candidates, sources, criteria, guidance, bounds and output location. It adds no runtime or domain guidance.

> Compare these supplier proposals against this brief. Identify missing evidence and comparable total costs. Recommend only when supported; do not place an order.

## Compose

Design Loop uses comparison in `test-increment`. A personal decision-brief workflow can apply `shared:compare-candidates`, write a recommendation from its evidence, then apply core `orchflows:orch-review-revise-once` to that draft. Return the comparison, original review, delivered recommendation and gaps. Keep reporting preferences in personal guidance.

Comparison and revision have different owners: this package owns comparison; core owns bounded review/revision. There is no shared revision alias. Each can be used directly or inside a larger workflow under the core composition contract.

## Validation

The [composition fixture](trials/composition/request.md) now calls core revision directly. Earlier Codex and Claude trials ran frozen versions with the former alias; [trial records](trials/README.md) preserve those observations and output failures. They do not validate every current byte. Expectations are evaluator-only, and native registration is separate from file-based execution.
