# Design craft

Framework specifics live with the workspace's standards owner.

## Vocabulary

- **view** — one independently renderable unit: a route, page, or
  component; the ticket's unit of work.
- **view identity** — view × breakpoint × state at a revision; what a
  capture shows, a verdict covers, and a golden capture pins.
- **breakpoint** — a named viewport width where layout decisions may
  change; the spec's breakpoint set closes the list.
- **state** — one interaction or data condition of a view: hover,
  focus, disabled, empty, loading, error, overflow; enumerated per
  view, each one rendered, never assumed.
- **capture** — the saved rendered image at one view identity; the
  only evidence a visual verdict accepts. A fresh capture returns a
  `capture-artifact` identity (view, breakpoint, state, `sink:` locator,
  and digest), never a path in mutation scope.
- **golden capture** — an approved capture frozen as the baseline for
  one view identity; the visual analog of a pinned hash.
- **token** — a design token: the single named carrier of one visual
  decision (a color, a space, a size, a duration); one name per
  decision; a hard-coded value where a token exists is synonym drift.
- **scale** — the closed, ordered set of steps a token kind draws from
  (type scale, spacing scale); values land on steps, never between.
- **design language** — the dimensions a judge scores: palette, type,
  spacing rhythm, density, motion, hierarchy — the order attention
  lands on a view, carried by size, weight, contrast, and position,
  never by source order alone.
- **accessibility bar** — the floor of contrast, focus visibility and
  semantics, plus the exact check command deciding it.
- **affordance** — what an element's appearance promises about
  interaction; kept when the behavior behind it matches the promise.

## Lens

- Design language: every view holds the spec's design language on
  each scored dimension, at every breakpoint.
- Hierarchy: attention lands in the design language's stated order at
  every covered identity, and focus order follows it.
- Tokens: sampled rendered values trace to tokens and land on their
  scales.
- States: every enumerated state has a capture; every affordance's
  promise is kept by the behavior behind it.
- Accessibility: the bar holds past its check command — meaning survives
  without color, and keyboard reach matches pointer reach.
- Consistency: one decision resolves one way on every view;
  cross-view drift is the finding class only this lens sees.
