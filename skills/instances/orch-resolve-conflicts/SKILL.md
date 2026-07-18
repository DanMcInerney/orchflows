---
name: orch-resolve-conflicts
description: Rule each merge or rebase conflict from both sides' evidence. The code pack's conflict instance.
role: worker
---

Require: a workspace in a conflicted merge or rebase state.

Per conflict: read both sides' intent from their own commits, tests,
and tickets — never from the surface diff alone. Rule for the side
whose intent the evidence supports, or compose both when they are
orthogonal; a ruling states which intent won and why. When both sides'
evidence genuinely conflicts on purpose, not text, stop and return the
conflict as `blocked` with both intents — that is a decision, not a
merge.

After all rulings, run the workspace's cheapest deterministic oracle;
a resolution that breaks the build is not a resolution.

Never: pick a side by recency or size; invent a third behavior neither
side had; leave a conflict marker behind.

Return: per-conflict rulings with evidence, the oracle result, and any
blocked conflicts with both intents.
