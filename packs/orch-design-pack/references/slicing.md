# Design slicing: token-first view tickets

Cut the spec into view tickets: the token set plus one core view
first — the tracer analog, proving the design language end to end and
exempt from the one-view rule below — then widen to the remaining
views.

- Each ticket is one view with its full identity set (the spec's
  breakpoints × its enumerated states), provable by capture and the
  ticket's deterministic checks; dependency edges where one view
  composes another.
- Each view item repeats verbatim its identity list, its render,
  capture and diff commands, its accessibility bar and design
  language, and the standards owner pointer.
