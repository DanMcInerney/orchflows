# Design craft

The design domain's terms and shape, per the signature's craft cell.
Framework-free the way content craft is genre-free: each term binds a
marketing page, a dashboard, and a component library equally; framework
specifics live with the workspace's standards owner.

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
  only evidence a visual verdict accepts.
- **golden capture** — an approved capture frozen as the baseline for
  one view identity; the visual analog of a pinned hash.
- **token** — a design token: the single named carrier of one visual
  decision (a color, a space, a size, a duration); one name per
  decision, so exact search finds every use of it; a hard-coded value
  where a token exists is synonym drift.
- **scale** — the closed, ordered set of steps a token kind draws from
  (type scale, spacing scale); values land on steps, never between.
- **design language** — the spec field of this name: the dimensions a
  judge scores — palette, type, spacing rhythm, density, motion.
- **hierarchy** — the order attention lands on a view; stated in the
  spec, judged from captures, carried by size, weight, contrast, and
  position, never by source order alone.
- **affordance** — what an element's appearance promises about
  interaction; kept when the behavior behind it matches the promise.
- **accessibility bar** — the spec field of this name: the floor —
  contrast, focus visibility, semantics — and the exact check command
  that decides it.

## Shape

What a metered, search-navigating reader pays least for, rendered:

- Token before value: every visual decision is made once, at a token,
  and referenced everywhere; a per-element exception is a defect
  unless the standards owner grants it.
- A view owns its states end to end: all states co-located with the
  view; understanding one component never scatters across layers.
- Flat composition: breadth over depth; add a wrapper only behind a
  contract strong enough that readers never descend past it.
- Design for the capture: quality a capture at a named identity
  cannot show is shaped wrong, whatever its elegance in source.
- Empty, loading, and error are states of the view, not afterthoughts;
  a state the spec enumerates and no capture shows is unfinished work.
