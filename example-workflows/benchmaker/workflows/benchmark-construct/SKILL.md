---
name: benchmark-construct
description: Construct a runnable benchmark draft from independent target and field evidence inside benchmaker.
disable-model-invocation: true
---

Require: `target`, observable `outcome`, licensed `sources` policy including
recency/access limits, evidence-defined `rigor`, domain construction `standard`,
fixed `target_configuration`, preregistered `calibration_policy`, destination
`package` and git `workspace`, evidence-store root, source/tool and execution
bounds. Missing inputs return partial evidence and named gaps before dependent
making; no inferred configuration or policy.

    tickets.py frame-open <run> --goal-file <construction-goal> --workflow benchmark-construct

This benchmaker-private journal preserves the research-to-draft handoff.

## Research

Give each lane the complete target/outcome, source policy, rigor, configuration,
calibration policy, store root and bounds through Goal/Details/Context. Declare
these numbered sub-questions in their research root:

1. **Target:** Which claims, observable failures, boundaries and harness/history
   define the target's intended construct?
2. **Field:** Which prior suites, failure taxonomies, oracle precedents and
   contamination records constrain that construct?

One independent context and isolated evidence-store lane per question:

    tickets.py do <run> --parent <frame> --standard benchmark-evidence --goal-file <target-lane>
    tickets.py do <run> --parent <frame> --standard benchmark-evidence --goal-file <field-lane>

Launch together. After both return, supply their actual packet identities and
the original semantic inputs to synthesis; a missing packet returns partial
research rather than invented convergence.

    tickets.py do <run> --parent <frame> --standard benchmark-evidence --goal-file <synthesis>

## Design

Hand the synthesis identity and original inputs to one design maker:

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <design>

Fix a committed development design before materialization: dataset class
(mined/authored/generated-then-filtered), claim/case/gap mappings, coverage
strata/floors/weights, split/access classes, sourcing ancestry, calibration
sampling/revision/sample budget, candidate-visible interface, reference/oracle
specifications, scoring, execution tiers and cost. Carry configuration unchanged.
This fixes construction inputs; it is not the later evaluation freeze.

## Materialize

Give a separate isolated maker that design identity, synthesis and original
inputs; write every specified component into package using the
[v2 manifest](../../references/manifest.md).

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <materialize> --isolation required

Land the draft with runnable cases, runner, scoring, references, controls and
provenance; reserve external record locators and the draft qualification-pending
marker. Construction failures retain completed packets/design/components and gaps.
Record `unjudged: independent qualification belongs to the caller` for this
construction composition.

Never: mutate target; substitute research summaries for packet identities;
fabricate missing evidence; run target calibration here; label this draft
qualified, calibrated or protected without evidence.

Return: `tickets.py frame-close <run> <frame>` with committed draft and design
identities when available, research synthesis and lane identities, component
locators, pending qualification, spend and explicit gaps (`[]` when none).
