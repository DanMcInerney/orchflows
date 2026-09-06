---
name: final-acceptance
description: Judge the integrated production game against prompt, play, presentation, asset, and performance evidence.
disable-model-invocation: true
---

Require: fixed integrated `artifact:` identity, accepted core baseline,
production asset manifests, immutable traceability and [final rubric](../../references/final-rubric.md),
complete capture matrix, every required play account, qualified performance
cells, QA result, and parent frame journal.

Read the journal, freeze the evidence index, and judge the joined candidate:

    tickets.py judge <run> --standard threejs-browser-game --standard browser-game-3d-asset --standard browser-game-interface --standard browser-game-playtest --parent <frame> --artifacts <integrated-artifact> --goal-file <final-judge-goal> --isolation required

The final gate requires a browser-served production build without developer
tools, documented controls, every prompt-derived mechanic and state, approved
assets with closed provenance, no blocking console, network, or load errors,
adaptive play from at least two independent contexts, complete
boot/entry/combat/progression/boss or terminal/win-loss/restart/re-entry
captures, and every declared performance cell. It scores
presentation, play, prompt fidelity, and performance only from indexed
evidence. Static surfaces report counts without an FPS claim.

For a blocking verdict, relay its complete `findings:` line to one bounded
repair and repeat affected QA, play, capture, and judgment. A batch permits
two repair/re-judge rounds. If re-judge still blocks, the parent opens one
automatic successor with the complete append-only complaint ledger, fixed
criteria, and best artifact identity; permission is unnecessary. A second
blocked re-judge ends the batch and routes its disposition through the parent:

- `fix` opens the next bounded repair with only accepted complaints and their
  regression checks;
- `redesign` returns to discovery with a new concept revision and named
  invalidations; and
- `unverified` opens missing-evidence acquisition or a capable execution
  context, preserving narrower evidence until it is observed.

Every route appends its findings, cause, evidence, expected improvement, and
exact resume state before continuing or stopping.

    tickets.py do <run> --standard threejs-browser-game --parent <frame> --goal-file <final-repair-goal> --isolation required
    tickets.py judge <run> --standard threejs-browser-game --standard browser-game-3d-asset --standard browser-game-interface --standard browser-game-playtest --parent <frame> --artifacts <repaired-artifact> --goal-file <final-rejudge-goal> --isolation required

Keep complaint IDs append-only; diagnose stagnation or oscillation with a
changed strategy; preserve the best fixed revision, unresolved findings, and
resume state at an external or budget limit. A performance miss repeats the
identical cell after one causal repair. An evidence loss,
ambiguous canvas attribution, trace mismatch, or gameplay-changing asset is
`unverified` until its boundary is repaired.

Never average contradictory evidence, waive a hard gate for attractive art,
or call scripted input actual play. The independent final gate may pass its
fixed source before the outside probe runs; public workflow completion may
claim final acceptance only after the outside probe observes that joined
revision. Keep the pending outside status, fixed identities, and gate evidence
visible between those two checks.

Return: completed ticket carrying `artifact:` for the best or accepted final
revision, final gate-verdict and evidence-index identities, complaint ledger,
outside-probe requirement, disposition, gaps, and exact resume state.
