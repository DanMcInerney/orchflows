---
name: renovate
description: Improve an existing workspace without a user-supplied spec.
disable-model-invocation: true
---

Require: `workspace`, the repository being improved; `priorities`, the
maintainer's lens, which stands in for the spec nobody wrote; `audit_bound`
and `brief_bound`, the two budgets; and `pack`, the stamp every call here
carries.

    tickets.py frame-open <run> --goal-file <renovation-goal>

Re-read the frame's `## Report` and its children before each call, then
append the decision with `tickets.py result <run> <frame> --by <frame>`.
Keep every returned `artifact:` and `findings:` line verbatim.

**Audit**, read-only, its typed artifact line the workspace tip:

    tickets.py judge <run> --pack <pack> --parent <frame>
      --artifacts git:<workspace-tip-sha> --goal-file <audit-goal>
      --isolation required --bound <audit_bound>

Its goal: an independent blocker report over `workspace` under
`priorities` — the pack's check craft applied, and every evidence-backed
blocker reported.

**Triage**, one further `judge --pack <pack>` handed the audit's
`findings: <path>` line verbatim: every finding carries one disposition, and
every ready-for-agent finding carries a compacted brief a fresh context can
execute from. Triage spends only the cheap checks it licenses; a finding
that needs more investigation is dispositioned as needing it, not
investigated here.

**Deliver**, one call over every ready-for-agent brief rather than one per
brief, so the verification runs once over the whole delivery:

    tickets.py do <run> --pack <pack> --parent <frame> --isolation required
      --goal-file <delivery-goal> --bound "<brief_bound> per brief"

Its goal quotes the triage findings and asks for every ready-for-agent brief
delivered into `workspace` with its own final verification, and every
ready-for-human brief returned to the maintainer unanswered.

Never: deliver a brief triage did not disposition ready-for-agent; answer a
ready-for-human brief on the maintainer's behalf; investigate a finding past
the cheap checks triage licenses; or close the frame on the delivery's own
claim of its verification.

Return: `tickets.py frame-close <run> <frame> --done <check>`, whose done is
the workspace's own required checks at the delivered revision — read
outside the delivery, as an exit code.
