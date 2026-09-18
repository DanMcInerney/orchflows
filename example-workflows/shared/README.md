# Shared comparison

Compare stable alternatives under caller criteria and guidance.

| Component | Result |
| --- | --- |
| [compare-candidates](skills/compare-candidates/SKILL.md) | Evidence, coverage gaps and a supported preference; no adoption or candidate edits |

## Use and dependencies

Requires core 0.12.0+ and native independent review; see [library context](references/library-context.md). Install from the checkout:

```sh
python scripts/orchflows.py setup --example shared
```

Register using core `docs/hosts.md`. Invoke `$shared:compare-candidates` in Codex or `/shared:compare-candidates` in Claude with candidates, sources, criteria, guidance, bounds and output location. No runtime or domain guidance is bundled.

> Compare these supplier proposals against this brief. Identify missing evidence and comparable total costs. Recommend only when supported; do not place an order.

## Compose

Design Loop uses comparison in `test-increment`. A personal decision brief can compose `shared:compare-candidates` → draft from evidence → core `orchflows:orch-review-revise-once`, returning comparison, original review, delivered recommendation and gaps. Personal guidance owns reporting preferences.

This package owns comparison; core owns bounded review/revision. There is no shared revision alias. Both compose under core's contract.

## Validation

The [composition fixture](trials/composition/request.md) calls core revision directly. Earlier frozen Codex/Claude trials used the former alias; [records](trials/README.md) retain observations and output failures, not validation of current bytes. Expectations are evaluator-only. File-based execution does not verify native registration.
