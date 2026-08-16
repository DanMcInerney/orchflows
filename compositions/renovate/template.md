---
name: renovate
description: Improve an existing workspace without a user-supplied spec.
entry: named
placeholders: [workspace, priorities, audit_bound, brief_bound, pack]
---

Improvement where nobody wrote a spec: the maintainer's priorities are
the lens, the audit finds what is wrong, triage decides which findings
an agent may take, and each of those is delivered and verified.

Three stubs, one chain: `00-audit` → `01-triage` → `02-deliver`.
`02-deliver` is terminal, so its completion test is this template's done
check — every disposition landed, agent briefs delivered with their
final verification and human briefs returned to the maintainer.

Instantiate with `workspace`, `priorities`, the two bounds, and `pack`.
Both bounds are placeholders because a brief cut without its bound
already fixed is renovation as an unconverging loop wearing a different
name, which is why `00-audit` and `02-deliver` each carry that excluded
action. The run's bound is `00-audit`'s `audit_bound` plus
`02-deliver`'s `brief_bound` per ready-for-agent brief: the delivery
root's bound is that per-brief budget, never one brief's for all of
them. `pack` is one because `02-deliver` is a root ticket, and a root
ticket without a stamp is one `orch-decompose` rejects at dispatch — the
run's pack, since its cut stamps a unit whose brief kind differs.
Each stub is a ticket per
[contracts/work-item.md](../../contracts/work-item.md) missing only what
instantiation adds.
