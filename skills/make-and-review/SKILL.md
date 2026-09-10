---
name: make-and-review
description: Make a requested result through delegated work, independent review and a bounded repair pass.
---

Choose the standards relevant to the request. Load [delegate-work](../delegate-work/SKILL.md) to make the result, then [delegate-review](../delegate-review/SKILL.md) to inspect that result against the same outcome and standards.

If the review finds substantive defects, use native continuation to ask the maker to repair them, carrying the findings and applicable standards. Then obtain one fresh independent review of the revised work. This example stops after that repair pass; describe any unresolved defects rather than silently repeating it.

For repository changes, bring the chosen result into the intended branch with native host tools or Git and check the combined result. Preserve useful work before cleanup. Tell the user what was made, what was checked and what remains uncertain.
