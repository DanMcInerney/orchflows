---
name: orch-workspace
description: Establish one isolated workspace with proven provenance and a clean baseline before any run writes anything.
role: worker
---

Require: the target per the stamped pack's workspace cell, and the run
id.

Establish isolation wholly per the stamped pack's workspace cell — the
cell states the mechanism; this skill enumerates none. Where the
dispatch that carries isolation is what creates the workspace, the
establishing instance is the child dispatched into it, never the
caller that asked for it: a caller outside can ask for isolation, only
an instance inside can prove what it got. Prove provenance: record
what the workspace derives from, by identity. Prove the baseline
clean: run the pack's cheapest deterministic oracle (or record the
starting identities where none exists) so later failures are
attributable to the run, not the starting state. Grade the isolation
declaration at the join with `scripts/workspace.py check <run> <id>
--base <rev>`, where the base is the revision the item was dispatched
from; the check runs before the merge, because afterwards the item tip
is already an ancestor of the run tip and a stamped item exits clean
by design.

Never: write into a shared workspace; proceed on a dirty baseline
without recording exactly what was dirty; report a workspace as
established on evidence observed from outside it — that is requested,
not verified ([profiles.md](../orch-delegate/references/profiles.md)).

Return: workspace identity, provenance, and baseline evidence.
