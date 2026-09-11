---
name: orch-make-and-review
description: Make a requested result through delegated work, independent review and a bounded repair pass.
---

Use [orch-record-run](../orch-record-run/SKILL.md) for one outer `orchflows-light:orch-make-and-review` run when a configured home is available. Reuse a caller's run/output context across composition and workers; finalize only a run owned here with the actual outcome. If history setup is absent, state the gap and continue the requested work.

Choose the standards relevant to the request. Load [orch-work](../orch-work/SKILL.md) to make the result, then [orch-review](../orch-review/SKILL.md) to inspect that result against the same outcome and standards.

If the review finds substantive defects, use native continuation to ask the maker to repair them, carrying the findings and applicable standards. Then obtain one fresh independent review of the revised work. This example stops after that repair pass; describe any unresolved defects rather than silently repeating it.

For repository changes, bring the chosen result into the intended branch with native host tools or Git and check the combined result. Preserve useful work before cleanup. Tell the user what was made, what was checked and what remains uncertain.
