# Design slicing: token-first view tickets

The token set alone opens the first frontier. Every view's capture
samples rendered values against the tokens, so each view the
acceptance enumerates by breakpoint and state depends on that item
under [rules/topology.md](../../../rules/topology.md) §3's edge rule
and takes the frontier behind it. Pair the tokens with one core view,
exempt from the one-view rule below, only while the design language
stays unproven.

- Each ticket is one view with its full identity set (the spec's
  breakpoints × its enumerated states), provable by capture and the
  ticket's deterministic checks; dependency edges where one view
  composes another.
- Each view item repeats verbatim its identity list, its render,
  capture and diff commands, its accessibility bar and design
  language, and the standards owner pointer.
