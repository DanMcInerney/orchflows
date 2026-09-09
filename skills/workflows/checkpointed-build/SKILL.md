---
name: checkpointed-build
description: Build one artifact in planned waves — a cut, isolated making per wave, one judge over the joined tip, bounded repair, closed on a probe.
disable-model-invocation: true
---

Require: `goal`, what is being built and what would make it done; `standard`,
stamped on the making; `judge-standard`, stamped on the judge; `narrowings`,
the names both of those also stamp, `[]` when none; `probe`, the command that
answers whether the built artifact works; `bound`, each call's budget; and
`workspace`, the repository the waves cut from.

Optional `context-file` accompanies every call, including repairs.

    tickets.py frame-open <run> --goal-file <build-goal> --workflow checkpointed-build
      [--context-file <context-file>]

**Plan**, one call whose artifact is the cut:

    tickets.py do <run> --standard <standard> --parent <frame> --makes cut
      --goal-file <plan-goal> [--context-file <context-file>] --workspace <workspace> --bound <bound>

Its goal: `goal` cut into waves, every item of a level independent of its
siblings and every dependency edge an earlier wave's seam. The first wave
pins the artifact's dependency set — each library, its version and the
lockfile the artifact will carry. A later wave needing one more reports the
addition as a deviation with the evidence that forced it; nothing else adds
one.

**Waves**, in the cut's order, one per level:

    tickets.py do <run> --standard <standard> --parent <frame> --isolation required
      [--standard <narrowing> ...] --goal-file <item-goal> [--context-file <context-file>]
      --workspace <workspace> --bound <bound>

*fan-out*: "One `do` per named item, launched together under the frame; the
shape line lists them as one wave." Each item's goal names the earlier
waves' artifacts as its input. The next wave opens only once every call of
this one has landed, and that landing is the checkpoint: what the level was
cut to make either exists in `workspace` or the wave is repeated, never
skipped past.

**Review.** Invoke `review-delivery` in this existing frame over the
joined tip, with `goal`, evidence, `judge-standard` and `narrowings`, `workspace`,
`bound`, outside `probe`, original `context-file`, `workspace-adapter` git,
and `isolation` required. The delivery parent's policy governs nested builds.
An unresolved review returns its disposition and best artifact; it never
opens an automatic successor review.

Never: leave `workspace` off any call of this frame — the run's integration
target is fixed by its first establishment, so a call that defaults it sends
every later wave's merge at the driver's own tree; open a wave the cut did not
place at that level; make in a shared tree; hand the judge a standard the waves did not carry, or a candidate rather
than the joined tip; add a dependency the first wave did not pin without
reporting the deviation; or close on anything but *outside-close*: "Close on
a command run outside every child; never on a child's own claim."

Return: `tickets.py frame-close <run> <frame> --done <probe>` over the
joined tip, `artifact: git:<tip>` beside the judge's verdict.
