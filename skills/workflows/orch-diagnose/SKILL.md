---
name: orch-diagnose
description: Find the proven cause of a failure through a reproducible feedback loop. Use before any fix when the cause is not known.
role: none
---

Require: the observed failure and access to where it occurs.

Establish a deterministic reproduction first — it is the entry oracle;
without it every later claim is UNVERIFIED. Then run `orch-loop`, goal
the proven cause, with body orch-investigate over cause hypotheses — a
caller-set bound, the packet carrying the killed-hypothesis digest:
each iteration one hypothesis, killed or confirmed by evidence the
reproduction can show — a hypothesis no experiment can decide is
parked, not argued. The done-check, deterministic: the candidate
cause, toggled, toggles the failure. Exits follow
[rules/loops.md](../../../rules/loops.md).

Never: declare a cause the reproduction cannot demonstrate; fix while
diagnosing; discard a killed hypothesis's evidence (the next lane needs
it).

Return: the proven cause with its toggle evidence, the reproduction,
and the hypothesis trail.
