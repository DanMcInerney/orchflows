---
name: orch-workspace
description: Establish one isolated workspace with proven provenance and a clean baseline before any run writes anything.
role: worker
---

Require: the target per the stamped pack's workspace cell, and the run
id.

Establish isolation wholly per the stamped pack's workspace cell — the
cell states the mechanism; this skill enumerates none. Prove
provenance: record what the workspace derives from, by identity. Prove
the baseline clean: run the pack's cheapest deterministic oracle (or
record the starting identities where none exists) so later failures
are attributable to the run, not the starting state.

Never: write into a shared workspace; proceed on a dirty baseline
without recording exactly what was dirty.

Return: workspace identity, provenance, and baseline evidence.
