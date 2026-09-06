---
name: discovery
description: Audit a 3D game brief, run independent research lanes, and freeze a traceable core design.
disable-model-invocation: true
---

Require: `brief`, `workspace`, package identity, and the parent frame journal.
The brief plus explicit amendments remains the authority; empirical choices
carry evidence and user-only uncertainty stays an exact question.

Read the journal, then launch one independent `do` for each question cluster:

    tickets.py do <run> --standard orch-research --skill research-acquire --parent <frame> --goal-file <mechanics-goal>
    tickets.py do <run> --standard orch-research --skill research-acquire --parent <frame> --goal-file <threejs-goal>
    tickets.py do <run> --standard orch-research --skill research-acquire --parent <frame> --goal-file <blender-goal>
    tickets.py do <run> --standard orch-research --skill research-acquire --parent <frame> --goal-file <play-evidence-goal>

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
