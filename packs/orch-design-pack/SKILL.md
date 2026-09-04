---
name: orch-design-pack
description: Domain pack for rendered interfaces — render evidence, git workspace. Stamp when the deliverable is judged as rendered.
adapter: git
---

# orch-design-pack

## Making

Framework specifics live with the workspace's standards owner.

## Vocabulary

- **view** — one independently renderable unit: a route, page, or
  component; the ticket's unit of work.
- **view identity** — view × breakpoint × state at a revision; what a
  capture shows, a verdict covers, and a golden capture pins.
- **breakpoint** — a named viewport width where layout decisions may
  change; the spec's breakpoint set closes the list.
- **state** — one interaction, data, or user-preference condition of a
  view: hover, focus, disabled, empty, loading, error, overflow,
  reduced motion, forced colors; enumerated per view, each one
  rendered, never assumed.
- **capture** — the saved rendered image at one view identity; the
  only evidence a visual verdict accepts.
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

## Workspace

git: a candidate diff pairs with fresh captures at the exact viewport,
and the pair is the view identity; render conflicts and contested
captures regenerate once at the join.

## Spec fields

repository; render/capture/diff commands; views by breakpoint/state;
language; accessibility bar; golden identities (none greenfield);
standards owner pointer

## Lens

### root

#### What a frozen design root carries

- A closed breakpoint set, plus the states each view is required to render
  rather than have assumed for it.
- Executable render, capture and diff commands, each marked pre-existing or
  to-be-authored; a visual bar nothing can run is an opinion held for later,
  not something frozen.
- An accessibility floor with the command deciding it, and either golden
  identities or their deliberate absence on greenfield.

#### Worth asking at intake

- Which views are in, at which breakpoints, in which states?
- What settles "right" here — an approved baseline, a token scale, or a judge?
- Which design-language dimensions get scored, and in what attention order?
- Does anything already rendered count as approved, or does this start empty?

#### Exemplar policy

Hand over one capture, or one live view identity, together with the dimensions
it stands for. An image with nothing attached settles nothing later, when two
readers take it two ways.

### cut

Token-first view tickets: the token set alone opens the first frontier.
Every view's capture samples rendered values against the tokens, so each
view the acceptance enumerates by breakpoint and state depends on that
item under [rules/topology.md](../../rules/topology.md) §3's edge rule
and takes the frontier behind it. Pair the tokens with one core view,
exempt from the one-view rule below, only while the design language
stays unproven.

- Each ticket is one view with its full identity set (the spec's
  breakpoints × its enumerated states), provable by capture and the
  ticket's deterministic checks; one view composing another is the
  only edge.
- Each view item carries by pointer its identity list, its render,
  capture and diff commands, its accessibility bar and design
  language, and the standards owner — never a copy.

### git

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

Identify the render and its covered view, breakpoint, and state matrix. Record
fresh captures, exercised interactions, console and accessibility readings,
relevant build output, and uncovered states.

Weigh in listed order, except that the accessibility floor is a bar rather
than a dimension the others trade against.

## Stages

- Enumerate view identities before editing: view, breakpoint and state
  are a closed capture set, including empty, loading, error and focus.
- Implement one renderable identity at a time and capture it at the exact
  viewport; a visual claim without a capture is unverified.
- Compare captures against tokens, scales and approved golden identities;
  record layout, type, contrast and interaction-state deltas.
- Regenerate only derived captures after a coherent change and keep their
  command, revision and dimensions with the evidence.
- Close with the capture inventory, measured checks, and remaining visual questions.
