# Design slicing: token-first view tickets

Cut the spec into view tickets: the token set plus one core view
first — the tracer analog, proving the design language end to end and
exempt from the one-view rule below — then widen to the remaining
views.

- Each ticket: one view with its full identity set (the spec's
  breakpoints × its enumerated states), provable by capture and the
  ticket's deterministic checks; its own isolated workspace at a clean
  baseline per the pack's workspace cell; dependency edges where one view
  composes another.
- Item extensions beyond the core: the identity list verbatim; the
  render, capture, and diff commands and the accessibility bar
  verbatim; the design language verbatim; the standards owner pointer.
- A view ticket missing a token returns `blocked` naming it — a
  token ticket precedes it as a dependency; it never hard-codes the
  value or widens its own scope.
- No terminal assembly item; cross-view consistency rides the gate's
  lens, never a ticket of its own.
- A design-language shift, touching most views at once, is the decision
  gap [rules/topology.md](../../../rules/topology.md) §3 names.
