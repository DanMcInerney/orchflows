# Renovate (non-normative example)

Improve an existing workspace without a user-supplied spec.

Audit: `orch-critique` over the workspace with the maintainer's stated
priorities as lens. Triage: `orch-triage` turns findings into
dispositions and compacted briefs. Deliver: each ready-for-agent brief
becomes a small spec through `orch-spec` and a bounded `orch-deliver`;
each ready-for-human brief returns to the maintainer.

The audit's bound and the per-brief bounds are fixed before the audit
runs; renovation without bounds is an unconverging loop wearing a
different name.
