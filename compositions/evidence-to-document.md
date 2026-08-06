---
name: evidence-to-document
description: The median knowledge task — postmortem, literature review, due diligence — as two chained single-pack runs, never one mixed run.
entry: named
---

Require: the knowledge request and evidence access.

Steps:
- research — `orch-deliver`, pack `orch-research-pack`; deliverable: a
  verified synthesis with claim-to-source trace.
- document — `orch-deliver`, pack `orch-content-pack`; the document's
  claims trace to the synthesis, whose claims trace to sources —
  provenance runs end to end.

Edges: seq research → document — the synthesis identity, frozen,
becomes the content spec's evidence.

Invariants — Never: gather new evidence in the content run — a gap
discovered while drafting is queued scope for a research follow-up
run, never an inline source hunt.

Done check: the document run's final verification, with every document
claim tracing through the synthesis to a source.

Return: status, result — the document identity, verification — the
final run's verdicts; then the synthesis identity and queued research
follow-ups.
