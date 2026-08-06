---
name: renovate
description: Improve an existing workspace without a user-supplied spec.
entry: named
---

Require: the workspace, the maintainer's stated priorities, the
audit bound, and the per-brief bounds — all fixed before the audit
runs.

Steps:
- audit — `orch-critique` over the workspace, the maintainer's
  priorities as lens.
- triage — `orch-triage` turns findings into dispositions and
  compacted briefs.
- deliver — per ready-for-agent brief: a small spec through
  `orch-spec`, a bounded `orch-deliver`; ready-for-human briefs return
  to the maintainer.

Edges: seq audit → triage → deliver — findings are triage's evidence;
each brief is a deliver spec's evidence.

Invariants — Never: start the audit or a brief without its bound
already fixed — renovation without bounds is an unconverging loop
wearing a different name.

Done check: every disposition landed — each agent brief delivered
with its final verification, each human brief returned.

Return: status, result — the delivered change identities,
verification — per-brief final verdicts; then dispositions returned
to the maintainer.
