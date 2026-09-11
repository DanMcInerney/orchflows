---
name: parallel-build
description: Implement separable work through concurrent native makers, then join and review their contributions.
---

Identify implementation pieces that can progress independently. Settle only the shared interfaces or dependency order needed to keep their contributions compatible; do prerequisite work first when another piece depends on its result.

Load [delegate-work](../delegate-work/SKILL.md) for each piece, launching native makers concurrently where supported. Give each a clear responsibility and relevant context, using the isolation it provides.

Gather their actual changes and check results. Load [make-and-review](../make-and-review/SKILL.md) in the current orchestrator with those contributions as inputs, asking its maker to join them and resolve integration issues. Review and check the combined behavior against the original request, including the boundaries between contributions.
