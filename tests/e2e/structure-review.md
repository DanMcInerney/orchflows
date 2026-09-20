# Structure review, 2026-09-20

A fresh read-only reviewer rechecked the [pilot results](gate-results.md), [next-stage preparation](next-stage-study.md), current instructions, and original Build/blocked-regression judgments. This is an evidence/design review, not a new native experiment or final authoring review of the revised checkout.

## Evidence limits

The original eight executions have four acceptable, two material-failure and two inconclusive assessments only after the documented scorer correction and separately attributed supplemental audit. They are development observations, not a reliability rate. The research and contract prompts explicitly supplied the dependency before implementation; their successes do not demonstrate unprompted unit discovery. The landing page had no reviewer, so it does not validate joined code/design/writing review. The seeded two-module repair does demonstrate one reviewer followed by one separate fixing worker on that candidate.

The blocked-authoring regression demonstrates one correct stop after clarifying the trial prerequisite. A complete successful Build → trial → authoring review → fresh reuse journey remains unverified. The next-stage packets have no native executions. Offline tests validate fixtures and the harness, not model adherence. Example workflows were inspected structurally, not executed.

## Resulting wording changes

| Owner | Responsibility |
| --- | --- |
| Architecture | Shared execution, review, composition, guidance-selection and settings contracts. |
| `orchflows.md` | Judgment about coherent units, useful reuse and clear instructions; how to author guidance and assess process design. |
| Build | Author a reusable artifact; finish representative trials; review once; conditionally assign one fixer; deliver evidence and gaps. |
| Dynamic | Plan and execute this task with core guidance; use Build for reusable authoring. |

Build's instruction to save inputs, dependencies, process, outputs and stopping conditions now explicitly applies to workflows. Guidance is exercised through actual consumers. Shared guidance now describes common quality criteria, optional Make/Review methods, useful domain specializations, placement of task/process/reference material and removable corrections. Existing guidance may be sufficient; a consuming skill does not automatically deserve a new guidance file.

Dynamic explicitly supplies all applicable task guidance to the reviewer of a joined candidate. Counts remain in the workflows that own them. The short repeated review/repair policy does not justify another primitive, mandatory component or per-skill guidance hierarchy.

The historical premature-review reminder was removed from `orchflows.md`; Build retains its explicit trial-before-review stop rule. **The successful regression included both instructions**, so reminder removal is an unvalidated concision change, not a demonstrated improvement. The direct-check exception and one-review/conditional-one-fixer policy remain unchanged. No model, host, registration or frozen evidence was changed.

This revision postdates the frozen next-stage packets. Those packets preserve the earlier wording and must not be described as trials of this revision. A later native comparison must identify its actual source and scenario hashes. Final authoring review remains pending under Build's required trial-before-review dependency.

Validation after the wording revision: `python -B -m unittest discover -s tests` ran 211 tests in 38.2 seconds: 210 passed, one platform skip. `git diff --check` passed. No new native model trial or behavior-improvement claim was made.
