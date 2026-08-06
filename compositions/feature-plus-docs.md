---
name: feature-plus-docs
description: Interleaved code and content, composed — never one mixed graph.
entry: named
---

Require: the feature request and its workspace.

Steps:
- code — `orch-deliver`, pack `orch-code-pack`.
- docs — `orch-deliver`, pack `orch-content-pack`; the spec describes
  the behavior that now verifiably exists.
- gate — one `orch-review-fix` over the combined fixed revision, one
  lane per lens — the code lens and the content lens — findings
  validated jointly, per [rules/topology.md](../rules/topology.md) §5.

Edges: seq code → docs → gate — code's result identity becomes the
content spec's frozen evidence; the gate takes both runs' combined
revision.

Invariants — Never: one mixed graph; a gate per domain —
cross-domain inconsistency (docs describing behavior the code does
not have) is the finding class per-domain gates structurally cannot
see, and the reason this composition exists.

Done check: the joint gate's verdicts over the combined revision,
cross-lens consistency included.

Return: status, result — the combined revision, verification — the
joint gate's verdicts; then both run identities.
