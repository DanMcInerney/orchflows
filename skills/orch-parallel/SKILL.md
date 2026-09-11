---
name: orch-parallel
description: Implement separable work through concurrent native makers, then join and review their contributions.
---

Use [orch-record-run](../orch-record-run/SKILL.md) for one outer `orchflows-light:orch-parallel` run when a configured home is available. Reuse a caller's run/output context across composition and workers; finalize only a run owned here with the actual outcome. If history setup is absent, state the gap and continue the requested work.

Identify implementation pieces that can progress independently. Settle only the shared interfaces or dependency order needed to keep their contributions compatible; do prerequisite work first when another piece depends on its result.

Load [orch-work](../orch-work/SKILL.md) for each piece, launching native makers concurrently where supported. Give each a clear responsibility and relevant context, using the isolation it provides.

Gather their actual changes and check results. Load [orch-make-and-review](../orch-make-and-review/SKILL.md) in the current orchestrator with those contributions as inputs, asking its maker to join them and resolve integration issues. Review and check the combined behavior against the original request, including the boundaries between contributions.
