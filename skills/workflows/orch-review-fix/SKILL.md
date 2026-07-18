---
name: orch-review-fix
description: One gate — review a fixed revision through stamped lenses, correct once, verify once. Every delivery crosses this exactly once.
role: none
---

Require: a fixed result identity; the stamped lens or lenses; the
pack's oracle policy; the spec; the standards owner by pointer, where
the workspace names one; the pack's craft reference; the write scope
the repair may touch.

Dispatch one read-only reviewer lane per lens, each its own delegation
packet over the same fixed revision, directly through `orch-delegate`
— each lane applies its lens via `orch-critique` or the lens's named
skill against the spec, the standards owner by pointer, and the craft
reference, criteria restated fresh from the spec, in a context
independent of whoever produced the revision; each lane's result
crosses `orch-integrate` as it lands. Once every lane has landed,
adjudicate the findings' combined content into the combined validated
set, grouped by shared cause per
[rules/verification.md](../../../rules/verification.md) §9 —
cross-lens inconsistency is a finding of its own. Spend at most one
correction pass through `orch-repair`, naming the `orch-worker`
profile, bounded to the write scope, on the combined validated set.
Close with one `orch-verify` over the affected criteria.

Never: a second correction pass (survivors return as findings); one
gate per lens or per domain; a reviewer lane that edits.

Return: validated findings with dispositions, the correction's changed
artifacts, anything repair queued, and the final verification.
