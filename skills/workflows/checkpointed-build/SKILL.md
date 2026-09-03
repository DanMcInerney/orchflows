---
name: checkpointed-build
description: Build one artifact in planned waves — a cut, isolated making per wave, one judge over the joined tip, bounded repair, closed on a probe.
disable-model-invocation: true
---

Require: `goal`, what is being built and what would make it done; `pack`,
stamped on the making; `judge-pack`, stamped on the judge; `sheets`, the
sheet names both of those stamp, `[]` when none; `probe`, the command that
answers whether the built artifact works; `bound`, each call's budget; and
`workspace`, the repository the waves cut from.

    tickets.py frame-open <run> --goal-file <build-goal> --workflow checkpointed-build

**Plan**, one call whose artifact is the cut:

    tickets.py do <run> --pack <pack> --parent <frame> --makes cut
      --goal-file <plan-goal> --workspace <workspace> --bound <bound>

Its goal: `goal` cut into waves, every item of a level independent of its
siblings and every dependency edge an earlier wave's seam. The first wave
pins the artifact's dependency set — each library, its version and the
lockfile the artifact will carry. A later wave needing one more reports the
addition as a deviation with the evidence that forced it; nothing else adds
one.

**Waves**, in the cut's order, one per level:

    tickets.py do <run> --pack <pack> --parent <frame> --isolation required
      --sheet <sheet> [--sheet ...] --goal-file <item-goal>
      --workspace <workspace> --bound <bound>

`fan-out` over that level's items, each handed the earlier waves' `artifact:`
lines. The next wave opens only once every call of this one has landed, and
that landing is the checkpoint: what the level was cut to make either exists
in `workspace` or the wave is repeated, never skipped past.

**Judge**, one call over the joined tip, carrying every sheet the waves
carried:

    tickets.py judge <run> --pack <judge-pack> --parent <frame>
      --sheet <sheet> [--sheet ...] --artifacts git:<tip>
      --goal-file <judge-goal>

Its goal: `goal` against that revision, each block named with the evidence
for it. Blocks earn `bounded-repair`.

Never: leave `workspace` off any call of this frame — the run's integration
target is fixed by its first establishment, so a call that defaults it sends
every later wave's merge at the driver's own tree; open a wave the cut did not
place at that level; make in a shared tree; hand the judge a sheet the waves did not carry, or a candidate rather
than the joined tip; add a dependency the first wave did not pin without
reporting the deviation; or close on anything but `outside-close`.

Return: `tickets.py frame-close <run> <frame> --done <probe>`, `probe` run
over the joined tip outside every child as an exit code, beside the judge's
verdict — `artifact: git:<tip>` and the judge's `findings:` line relayed
verbatim.
