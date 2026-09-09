---
name: review-delivery
description: End ordinary delivery with one owned review policy, repairs and scoped verification; repeat substantive critique only under selected rounds.
disable-model-invocation: true
---

Require: fixed joined `artifacts`; `goal` and its evidence; `standards`, the
pinned criteria for every critique and verification; `workspace`; `bound`;
and the delivery's existing `frame`, opened with `tickets.py frame-open`;
`probe`, its outside completion check. Optional `rounds` is a positive integer
or `until_pass`: explicit user choice overrides a named workflow setting,
then default one. Strictness changes standards, never rounds. The parent
seals rounds at creation; this helper inherits them. Read
[review policy](../../../docs/review-policy.md) for command carriers and migration.

Drive this recipe in that frame, preserving its package scope and journal;
do not open another public workflow frame. Standards resolve where this
existing frame's calls resolve. The caller owns the one close after the
recipe returns; this step creates no additional journal or review owner.

One round starts with substantive critique of the joined fixed artifacts:

    tickets.py judge <run> --parent <frame> --standard <standard>
      [--standard <narrowing> ...] --artifacts <typed-identity>
      --goal-file <critique-goal> --workspace <workspace> --bound <bound>

Pass ends the loop early. Otherwise hand accepted blocking findings and their
unchanged criteria to one repair wave, one or parallel making calls as the
findings require. Each repair goal contains the exact `findings:` line:

    tickets.py do <run> --parent <frame> --review-of <critique-ticket>
      --standard <standard> [--standard <narrowing> ...]
      --goal-file <repair-goal> --workspace <workspace> --bound <bound>

After every repair lands, verify the listed repairs and their affected seams
against the new joined identity. The verification goal names the original
findings, repair identities and affected checks; it never asks for a broad
critique. Run deterministic checks directly where sufficient; otherwise:

    tickets.py judge <run> --parent <frame> --review-of <critique-ticket>
      --standard <standard> [--standard <narrowing> ...]
      --artifacts <repaired-identity> --goal-file <verification-goal>
      --workspace <workspace> --bound <bound>

With allowance remaining, the parent may start the next substantive round.
Finite rounds count critiques, not workers or verification. `until_pass`
has no preset count; stop for a real external blocker or inability to make
progress, naming evidence and needed input. No score or reset substitutes
for that judgment. Keep criteria fixed throughout.

Never: let a helper or repair worker own another loop; silently add critique
after the selected allowance; repair nonblocking recommendations in this
delivery; turn verification into broad review; or call repaired output
freshly accepted when only its listed repairs were verified.

Return: `tickets.py frame-close <run> <frame> --done <probe>` for the caller's
successful close, joined artifact and findings lines, rounds consumed, and one truthful
ending: pass; repairs verified without a fresh overall verdict; exhausted
with unresolved findings; or blocked with evidence. An unresolved ending
returns the corresponding disposition instead of a successful close.
