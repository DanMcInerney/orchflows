# Design slicing: callable view tickets

Every ticket names one callable view with its full identity set (the
spec's breakpoints × its enumerated states). The first frontier pairs
the token set with one core view; later views depend on it under
[rules/topology.md](../../../rules/topology.md) §3's edge rule. A view
composed by another carries that dependency edge.

- Each view is provable by fresh captures and its deterministic checks.
- Each view item repeats verbatim its identity list, its render,
  capture and diff commands, its accessibility bar and design
  language, and the standards owner pointer.
