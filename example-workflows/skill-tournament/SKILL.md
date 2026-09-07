---
name: skill-tournament
description: Apply the evolve campaign to one fixed skill identity against a benchmark built and qualified for it.
disable-model-invocation: true
---

Require: `skill`, the fixed skill identity being evolved; `surface`, its
declared mutable surface, which belongs to the campaign and its candidates;
`policy`, the frozen search policy, promotion rule and margin; `bound`, the
campaign's budget, which the benchmark's own allocation is never drawn from;
and `sources`, `rigor`, `standard`, pinned `target_configuration` and preregistered
`calibration_policy`. Supply benchmark `package`/git `workspace`, external git
`evidence_workspace`, evidence-store root, native mechanism, `access_policy`,
qualification/reference-audit allocation and separate benchmark bounds.
Missing benchmark inputs stop before dependent work with named gaps.

One skill improves against one benchmark built and qualified for it —
*freeze*: "Fix the identity before any candidate exists and forbid every
later call from touching it." Both halves are workflows, not calls: each
opens its own frame under this one, and the ticket tree is the call tree.

    tickets.py frame-open <run> --goal-file <tournament-goal> --bound <bound> --workflow skill-tournament


**Build the benchmark.** Invoke `benchmaker` with `target=skill`, the
skill's declared observable outcome as `outcome`, and all benchmark inputs above,
including configuration/policy and both workspaces. The construction `standard`
must resolve in benchmaker's own scope; a tournament-private name cannot cross
this public boundary. Open its frame under this one and execute its body:

    tickets.py frame-open <run> --parent <frame> --goal-file <benchmark-goal> --workflow benchmaker

Enter the campaign only with revision-bound VALID qualification, CALIBRATED
development evidence meeting the declared policy, an eligible frozen git
revision, and final-evaluation evidence satisfying required rigor. Pending,
INVALID, UNVERIFIED, OUT_OF_BAND or legacy controls-only results stop here with
their evidence and gaps. Keep final score/drift separate from development
calibration. The eligible benchmark revision stays fixed for the campaign.

**Spend the campaign.** Invoke `evolve` under this frame the same way, with
`target=skill`, the skill's current fixed result/evidence as `incumbent`,
the benchmark's qualified revision plus `policy` as `evaluation`,
`writer=orch-do`, `mutation_scope=surface`, and `bound`. Its final score
card names the final incumbent and the one benchmark revision every
candidate was scored against.

Never: mutate `skill` — the benchmark is built for it, never by changing it;
generate, score or compare a candidate here, since both halves own that;
change the benchmark or the policy inside the campaign; restate or call
evolve's verification, search or selection internals; let a benchmaker frame
targeting benchmaker invoke evolve; or activate a selected result — that
requires a separate authorized integration.

Return: `tickets.py frame-close <run> <frame> --done <check>` over the
campaign's final score card and the fixed benchmark revision it cites.
