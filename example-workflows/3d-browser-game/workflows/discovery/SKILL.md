---
name: discovery
description: Audit a 3D game brief, run independent research lanes, and freeze a traceable core design.
disable-model-invocation: true
---

Require: `brief`, `workspace`, package identity, and the parent frame journal.
The brief plus explicit amendments remains the authority; empirical choices
carry evidence and user-only uncertainty stays an exact question.

First open `brief-intake` in this package with the original brief and workspace;
pass the returned identity as `intake-frame`, then close it after the helper returns:

    tickets.py frame-open <run> --parent <frame> --workflow brief-intake --goal-file <intake-goal>
    tickets.py frame-close <run> <intake-frame> --done <intake-check>

Carry its versioned decisions, experiments and checkpoint disposition into
research and design. Only dependent work waits on an unresolved user-only
question; the 3D stack is the public workflow's explicit constraint.

Invoke public `recent-search` once for each independent question cluster:
mechanics, Three.js, Blender, and play evidence. For each call supply
`output=evidence`, the cluster's bounded question and named public sources,
source policy and rigor bar, an explicit recent period or `all-time` where the
brief needs established technical facts, frozen horizon, per-step cap, isolated
evidence store, call bound, output probe, caller context and this parent frame.
Each invocation opens its own package scope:

    tickets.py frame-open <run> --workflow recent-search --parent <frame>
      --goal-file <cluster-question-goal> [--context-file <context-file>]

Drive that workflow with the supplied semantics; its private acquisition method
is resolved there, never from this game's package. Keep its evidence packets
and review findings for the synthesis.

Each lane records its bounded question, dated sources, counterevidence,
authorized spikes, confidence, disagreements, acquisition losses, and gaps
without reading another lane. Synthesize only after every launched result
returns. The synthesis `do` records the full prompt audit, capability
inventory, fun hypotheses, rules and state model, controls and camera,
progression, content beats, traceability rows, core/final rubrics, capture and
performance matrices, and a frozen core contract.

    tickets.py do <run> --standard orch-content --parent <frame> --goal-file <design-goal>

Write an explicit gap for missing image generation, Blender, browser control,
or performance attribution. A user-only gap is one verbatim question for the
root; independent research may continue while only dependent decisions wait.
The design record names all evidence identities and invalidation triggers.

Never compare engines or DCCs, invent support or licensing promises, create
production art before core acceptance, turn a research loss into a negative
claim, or let one lane choose another lane's conclusion.

Return: completed ticket and `artifact:` lines for the research packet,
capability inventory, frozen concept, traceability, rubrics, matrices, and
core contract, with `gaps: []` only when the recorded evidence supports that
claim.
